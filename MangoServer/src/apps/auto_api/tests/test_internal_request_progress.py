from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder as Recorder
from src.apps.auto_api.services.execution_trace.recorder import current_execution_trace


class InternalRequestProgressTests(SimpleTestCase):
    def recorder(self):
        recorder = Recorder()
        recorder.trace = SimpleNamespace(id=1, status=3, finished_at=None)
        recorder.start_step = Mock(return_value=Mock())
        recorder.finish_step = Mock()
        return recorder

    def test_only_completed_internal_calls_emit_bounded_progress_not_function_liveness(self):
        recorder = self.recorder()
        with patch('src.apps.auto_api.services.execution_trace.recorder.time.monotonic', return_value=0):
            recorder.record_request_progress()
            recorder.start_step.assert_not_called()
            with recorder.custom_function():
                recorder.start_step.assert_not_called()
                recorder.record_request_progress()
                recorder.record_request_progress()
            self.assertEqual(recorder.start_step.call_count, 1)
        with patch('src.apps.auto_api.services.execution_trace.recorder.time.monotonic', return_value=16):
            with recorder.custom_function():
                recorder.record_request_progress()
        self.assertEqual(recorder.start_step.call_count, 2)
        self.assertEqual(recorder.finish_step.call_count, 2)
        self.assertNotIn('response', str(recorder.start_step.call_args_list))

    def test_nested_function_error_restores_depth_without_creating_false_progress(self):
        recorder = self.recorder()
        with self.assertRaises(RuntimeError):
            with recorder.custom_function(), recorder.custom_function():
                raise RuntimeError('AUTO')
        self.assertEqual(recorder._custom_depth, 0)
        recorder.start_step.assert_not_called()

    def test_execution_scope_is_isolated_for_concurrent_cases_and_restored_on_error(self):
        def run(index):
            recorder = self.recorder()
            recorder.trace = SimpleNamespace(id=index)
            with recorder.execution_scope():
                self.assertEqual(current_execution_trace().id, index)
            self.assertIsNone(current_execution_trace())
            return index
        with ThreadPoolExecutor(max_workers=10) as pool:
            self.assertEqual(sorted(pool.map(run, range(100))), list(range(100)))
        self.assertIsNone(current_execution_trace())

    def test_scope_reads_trace_created_after_scope_entry(self):
        recorder = Recorder()
        with recorder.execution_scope():
            self.assertIsNone(current_execution_trace())
            recorder.trace = SimpleNamespace(id=17)
            self.assertEqual(current_execution_trace().id, 17)
        self.assertIsNone(current_execution_trace())

    def test_actual_request_adapter_reports_completion_but_not_transport_failure(self):
        import httpx
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest
        from src.apps.auto_api.enums import ApiProtocolTypeEnum
        from src.apps.auto_api.exceptions import AutoApiError
        from src.apps.auto_api.services.execution.base.api_base_test_setup.base_request import BaseRequest
        recorder = self.recorder()
        base = BaseRequest.__new__(BaseRequest)
        base.test_data, base.trace_recorder = None, recorder
        base.send_request = Mock(return_value=Mock(model_dump_json=Mock(return_value='{}')))
        prepared = SimpleNamespace(request_body=None, request_files=None, content_type=None, close=Mock())
        request = ApiExecutionRequest(method='GET', url='http://example.com',
                                      protocol_type=ApiProtocolTypeEnum.HTTP.value)
        with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.prepare_request_body',
                   return_value=prepared), recorder.custom_function():
            base.http(request)
            recorder.finish_step.assert_called_once()
            recorder.start_step.reset_mock()
            base.send_request.side_effect = httpx.ReadTimeout('AUTO_NETWORK')
            with self.assertRaises(AutoApiError):
                base.http(request)
            recorder.start_step.assert_not_called()
        self.assertEqual(prepared.close.call_count, 2)
