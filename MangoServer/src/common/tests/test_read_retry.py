from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import InterfaceError, OperationalError
from django.test import SimpleTestCase

from src.common.database.read_retry import read_with_connection_recovery


class ReadConnectionRecoveryTests(SimpleTestCase):
    def test_connection_loss_retries_read_once_on_new_connection(self):
        for error in (InterfaceError(0, ''), OperationalError(2006, 'private'), OperationalError(2013, 'private')):
            with self.subTest(error=type(error).__name__):
                connection = SimpleNamespace(in_atomic_block=False, close=Mock())
                read = Mock(side_effect=[error, {'id': 7}])
                with patch('src.common.database.read_retry.connections', {'default': connection}):
                    self.assertEqual(read_with_connection_recovery(read), {'id': 7})
                self.assertEqual(read.call_count, 2)
                connection.close.assert_called_once()

    def test_does_not_replay_transactions_or_non_connection_errors(self):
        for atomic, error in ((True, InterfaceError(0, '')), (False, OperationalError(1038, 'private')),
                              (False, OperationalError(1205, 'private')), (False, RuntimeError('private'))):
            with self.subTest(atomic=atomic, error=type(error).__name__):
                connection = SimpleNamespace(in_atomic_block=atomic, close=Mock())
                read = Mock(side_effect=error)
                with patch('src.common.database.read_retry.connections', {'default': connection}), \
                        self.assertRaises(type(error)):
                    read_with_connection_recovery(read)
                read.assert_called_once()
                connection.close.assert_not_called()

    def test_second_failure_is_preserved_without_infinite_retry(self):
        first, second = InterfaceError(0, ''), OperationalError(2013, 'private')
        read = Mock(side_effect=[first, second])
        connection = SimpleNamespace(in_atomic_block=False, close=Mock())
        with patch('src.common.database.read_retry.connections', {'default': connection}), \
                self.assertRaises(OperationalError) as raised:
            read_with_connection_recovery(read)
        self.assertIs(raised.exception, second)
        self.assertEqual(read.call_count, 2)
