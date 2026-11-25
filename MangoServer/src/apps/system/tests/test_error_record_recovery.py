from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import InterfaceError, OperationalError
from django.test import SimpleTestCase

from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
from src.common.enums.system_error import SystemErrorEventSource


class ErrorRecordRecoveryTests(SimpleTestCase):
    path = 'src.apps.system.services.runtime_center.system_error_event'

    def report(self):
        SystemErrorEventService.record_exception(RuntimeError('secret-original'), SystemErrorEventSource.MCP,
            request_path='tool:example', trace='secret-trace')

    def test_lost_connection_recovers_record_without_double_counting(self):
        for created in (False, True):
            with self.subTest(created=created), patch.object(SystemErrorEventService, 'record',
                    side_effect=InterfaceError(0, 'secret-db')) as record, \
                    patch(self.path + '.connection') as connection, \
                    patch(self.path + '.SystemErrorEvent') as model, patch(self.path + '.log') as logger:
                connection.in_atomic_block = False
                model.objects.get_or_create.return_value = (SimpleNamespace(pk=1), created)
                self.report()
                record.assert_called_once()
                connection.close.assert_called_once()
                model.objects.get_or_create.assert_called_once()
                defaults = model.objects.get_or_create.call_args.kwargs['defaults']
                self.assertEqual(defaults['exception_type'], 'RuntimeError')
                self.assertEqual(defaults['traceback'], 'secret-trace')
                if not created:
                    self.assertNotIn('count', model.objects.filter.return_value.update.call_args.kwargs)
                else:
                    model.objects.filter.return_value.update.assert_not_called()
                self.assertNotIn('secret', str(logger.mock_calls))

    def test_failed_recovery_keeps_sanitized_original_and_recording_diagnostics(self):
        with patch.object(SystemErrorEventService, 'record', side_effect=InterfaceError(0, 'secret-db')), \
                patch(self.path + '.connection') as connection, patch(self.path + '.SystemErrorEvent') as model, \
                patch(self.path + '.log') as logger:
            connection.in_atomic_block = False
            model.objects.get_or_create.side_effect = OperationalError(2013, 'secret-again')
            self.report()
            self.assertEqual(logger.system.error.call_count, 2)
            calls = str(logger.mock_calls)
            self.assertIn('RuntimeError', calls)
            self.assertIn('OperationalError', calls)
            self.assertIn('2013', calls)
            self.assertNotIn('secret', calls)

    def test_never_reconnects_inside_business_transaction_or_for_other_errors(self):
        for atomic, error in ((True, InterfaceError(0, '')), (False, OperationalError(1038, 'secret')),
                              (False, RuntimeError('secret'))):
            with self.subTest(atomic=atomic, error=type(error).__name__), \
                    patch.object(SystemErrorEventService, 'record', side_effect=error), \
                    patch(self.path + '.connection') as connection, patch(self.path + '.SystemErrorEvent') as model, \
                    patch(self.path + '.log'):
                connection.in_atomic_block = atomic
                self.report()
                connection.close.assert_not_called()
                model.objects.get_or_create.assert_not_called()
