import gc
import os
import weakref
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection


class ConnectionFinalizationTests(SimpleTestCase):
    def setUp(self):
        self.closed = patch('src.apps.data_factory.services.datasource.datasource_connection.DatasourceGovernorService.connection_closed').start()
        self.unknown = patch('src.apps.data_factory.services.datasource.datasource_connection.DatasourceGovernorService.finish_connection').start()
        self.addCleanup(patch.stopall)

    def test_garbage_collection_closes_socket_before_releasing_exact_permit(self):
        connection = Mock()
        permit = ('group', 'owner')
        wrapper = GovernedDbapiConnection(connection, permit)
        ref = weakref.ref(wrapper)
        self.closed.side_effect = lambda value: connection.close.assert_called_once()
        del wrapper
        gc.collect()
        self.assertIsNone(ref())
        self.closed.assert_called_once_with(permit)

    def test_explicit_close_then_gc_does_not_release_twice(self):
        connection = Mock()
        wrapper = GovernedDbapiConnection(connection, ('group', 'owner'))
        wrapper.close()
        del wrapper
        gc.collect()
        connection.close.assert_called_once()
        self.closed.assert_called_once()

    def test_child_process_cannot_finalize_parent_connection(self):
        connection = Mock()
        wrapper = GovernedDbapiConnection(connection, ('group', 'owner'))
        wrapper._creator_pid = os.getpid() + 100
        del wrapper
        gc.collect()
        connection.close.assert_not_called()
        self.closed.assert_not_called()

    def test_unconfirmed_close_never_releases_permit(self):
        connection = Mock()
        connection.close.side_effect = RuntimeError('close failed')
        with patch('src.common.logging.log.system.error'):
            wrapper = GovernedDbapiConnection(connection, ('group', 'owner'))
            del wrapper
            gc.collect()
        self.closed.assert_not_called()
        self.unknown.assert_called_once()
        self.assertTrue(self.unknown.call_args.kwargs['unknown'])
