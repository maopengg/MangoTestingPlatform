import json
from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.exceptions import ErrorDetail, ValidationError

from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID,
    AutoApiError,
)
from src.apps.system.services.runtime_center.system_error_event import (
    SystemErrorEventService,
    SystemErrorEventSource,
)
from src.common.decorators.system_error import system_error_guard


class SystemErrorEventClassificationTests(SimpleTestCase):
    def test_health_status_requires_explicit_recovery_evidence(self):
        states = [
            ({'active': False, 'resolved_at': 1794548254.0}, 'success', '已恢复'),
            ({'active': True, 'resolved_at': None}, 'error', '异常'),
            ({'active': True, 'resolved_at': 1794548254.0}, 'error', '异常'),
            ({'active': False}, 'error', '异常'),
            ({'active': 'false', 'resolved_at': 1}, 'error', '异常'),
            ({'active': False, 'resolved_at': True}, 'error', '异常'),
            ({'active': False, 'resolved_at': 0}, 'error', '异常'),
            ({'active': False, 'resolved_at': 'invalid'}, 'error', '异常'),
            ([], 'error', '异常'), (None, 'error', '异常'),
        ]
        for state, status, label in states:
            with self.subTest(state=state):
                item = SimpleNamespace(last_seen_at=timezone.now(), source='api-worker', id=1,
                                       request_path='datasource-health/example', service_name='api-worker',
                                       message='执行进展异常', exception_type='DatasourceExecutionHealth',
                                       traceback=json.dumps(state), count=2, fingerprint='example')
                data = SystemErrorEventService.serialize(item)
                self.assertEqual((data['status'], data['status_name']), (status, label))
                self.assertEqual(data['traceback'], item.traceback)
                self.assertEqual(data['count'], 2)

    def test_invalid_health_trace_and_ordinary_errors_remain_errors(self):
        for exception_type, trace in (
            ('DatasourceExecutionHealth', 'invalid JSON'),
            ('RuntimeError', '{"active":false,"resolved_at":1}'),
        ):
            item = SimpleNamespace(last_seen_at=timezone.now(), source='http', id=1, request_path='/api/example',
                                   service_name='core-api', message='error', exception_type=exception_type,
                                   traceback=trace, count=1, fingerprint='example')
            data = SystemErrorEventService.serialize(item)
            self.assertEqual((data['status'], data['status_name']), ('error', '异常'))
    @patch.object(SystemErrorEventService, 'record')
    def test_http_validation_is_sanitized_and_stable_for_deduplication(self, record):
        request = SimpleNamespace(method='POST', path='/api/example/config',
                                  data={'password': 'secret-request'}, headers={'Authorization': 'secret-header'})
        for secret in ('secret-one', 'secret-two'):
            error = ValidationError({'target_address': [ErrorDetail(secret, code='null')],
                                     'public_variable_ids': [ErrorDetail(secret, code='not_a_list')]})
            SystemErrorEventService.record_exception(error, SystemErrorEventSource.HTTP, request=request,
                                                      trace='secret-trace')
        self.assertEqual(record.call_count, 2)
        self.assertEqual(record.call_args_list[0], record.call_args_list[1])
        values = record.call_args.kwargs
        self.assertEqual(values['request_path'], 'POST /api/example/config')
        self.assertEqual(values['exception_type'], 'RequestValidationError')
        self.assertIn('target_address: null', values['message'])
        self.assertNotIn('secret', str(values))

    @patch.object(SystemErrorEventService, 'record')
    def test_duplicate_name_is_not_a_system_issue(self, record):
        SystemErrorEventService.record_exception(
            ValidationError({'name': [ErrorDetail('duplicate', code='unique')]}), SystemErrorEventSource.HTTP)
        record.assert_not_called()

    @patch.object(SystemErrorEventService, 'record')
    def test_nested_validation_is_bounded_and_does_not_expose_dynamic_keys(self, record):
        SystemErrorEventService.record_exception(
            ValidationError({'items': [{'secret@value': ['private-value']} for _ in range(500)]}),
            SystemErrorEventSource.DRF)
        values = record.call_args.kwargs
        self.assertNotIn('secret@value', str(values))
        self.assertNotIn('private-value', str(values))
        self.assertIn('items.field: invalid', values['message'])
        self.assertLess(len(values['trace']), 1000)

    @patch.object(SystemErrorEventService, 'record', side_effect=RuntimeError('private-db-error'))
    def test_validation_reporting_failure_does_not_break_request(self, record):
        SystemErrorEventService.record_exception(ValidationError({'name': ['bad']}), SystemErrorEventSource.HTTP)
        record.assert_called_once()

    def test_validation_uses_existing_status_and_storage_fields(self):
        now = timezone.now()
        item = SimpleNamespace(last_seen_at=now, source='http', id=1, request_path='POST /api/example/config',
                               service_name='core-api', message='校验失败', exception_type='RequestValidationError',
                               traceback='safe diagnostic', count=3, fingerprint='fingerprint')
        data = SystemErrorEventService.serialize(item)
        self.assertEqual(data['status'], 'warning')
        self.assertEqual(data['status_name'], '待排查')
        self.assertEqual(data['source_name'], '接口校验失败')

    @patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEvent')
    def test_repeated_validation_uses_atomic_counter_without_new_row(self, model):
        model.objects.filter.return_value.update.return_value = 1
        error = ValidationError({'target_address': [ErrorDetail('bad', code='null')]})
        SystemErrorEventService.record_exception(error, SystemErrorEventSource.HTTP,
                                                 request_path='POST /api/example/config')
        model.objects.create.assert_not_called()
        self.assertIn('count', model.objects.filter.return_value.update.call_args.kwargs)

    @patch.object(SystemErrorEventService, 'record')
    def test_business_error_is_not_recorded(self, record):
        SystemErrorEventService.record_exception(
            AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID),
            SystemErrorEventSource.SCHEDULER,
            request_path='dispatch_fire',
        )

        record.assert_not_called()

    @patch.object(SystemErrorEventService, 'record')
    def test_missing_object_is_not_recorded(self, record):
        SystemErrorEventService.record_exception(
            ObjectDoesNotExist('internal model name'),
            SystemErrorEventSource.MCP,
            request_path='tool:new_cli_compatible_tool',
        )

        record.assert_not_called()

    @patch.object(SystemErrorEventService, 'record')
    def test_unknown_error_is_recorded(self, record):
        error = RuntimeError('database unavailable')

        SystemErrorEventService.record_exception(
            error,
            SystemErrorEventSource.SCHEDULER,
            request_path='dispatch_fire',
            trace='traceback',
        )

        record.assert_called_once()
        self.assertEqual(record.call_args.kwargs['exception_type'], 'RuntimeError')
        self.assertEqual(record.call_args.kwargs['message'], 'database unavailable')

    def test_new_runtime_sources_have_display_names_and_services(self):
        self.assertEqual(
            SystemErrorEventService.resolve_service_name(SystemErrorEventSource.REALTIME),
            'realtime-service',
        )
        self.assertEqual(
            SystemErrorEventService.resolve_service_name(SystemErrorEventSource.MONITORING),
            'monitoring-service',
        )
        self.assertEqual(
            SystemErrorEventService.SOURCE_NAME_MAP[SystemErrorEventSource.REALTIME],
            '实时服务异常',
        )

    @patch.object(SystemErrorEventService, 'record_exception')
    def test_sync_guard_records_and_reraises(self, record_exception):
        @system_error_guard(
            source=SystemErrorEventSource.SCHEDULER,
            request_path='sync_operation',
            service_name='scheduler-service',
        )
        def operation():
            raise RuntimeError('sync failed')

        with self.assertRaisesRegex(RuntimeError, 'sync failed'):
            operation()

        record_exception.assert_called_once()
        self.assertEqual(record_exception.call_args.args[1], SystemErrorEventSource.SCHEDULER)
        self.assertEqual(record_exception.call_args.kwargs['request_path'], 'sync_operation')

    @patch.object(SystemErrorEventService, 'record_exception')
    def test_async_guard_records_and_reraises(self, record_exception):
        @system_error_guard(
            source=SystemErrorEventSource.REALTIME,
            request_path='async_operation',
            service_name='realtime-service',
        )
        async def operation():
            raise RuntimeError('async failed')

        with self.assertRaisesRegex(RuntimeError, 'async failed'):
            async_to_sync(operation)()

        record_exception.assert_called_once()
        self.assertEqual(record_exception.call_args.args[1], SystemErrorEventSource.REALTIME)
        self.assertEqual(record_exception.call_args.kwargs['request_path'], 'async_operation')
