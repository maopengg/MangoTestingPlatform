from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from django.test import SimpleTestCase

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
