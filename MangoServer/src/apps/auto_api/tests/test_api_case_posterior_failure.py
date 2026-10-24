from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.services.test_case.test_case import TestCase as ApiRuntimeTestCase


class ApiCasePosteriorFailureTests(SimpleTestCase):
    def build_runtime(self, original_error=None):
        runtime = ApiRuntimeTestCase.__new__(ApiRuntimeTestCase)
        runtime.case_id = 2754
        runtime.test_suite = 554996414321
        runtime.test_suite_details = 212763
        runtime.api_case = SimpleNamespace(posterior_sql=[{'value': 'DELETE'}], status=1)
        runtime.api_case_result = SimpleNamespace(status=1, error_message=original_error)
        runtime.case_base = Mock()
        runtime.case_base.case_posterior_main.side_effect = RuntimeError('缺少后置缓存变量')
        runtime.trace_recorder = Mock()
        runtime.trace_recorder.start_step.return_value = 'posterior-step'
        return runtime

    def test_posterior_failure_marks_case_failed_without_raising(self):
        runtime = self.build_runtime()

        runtime.run_case_posterior()

        self.assertEqual(runtime.api_case_result.status, StatusEnum.FAIL.value)
        self.assertEqual(runtime.api_case.status, StatusEnum.FAIL.value)
        self.assertEqual(runtime.api_case_result.error_message, '用例后置处理失败：缺少后置缓存变量')
        runtime.trace_recorder.fail_step.assert_called_once_with(
            'posterior-step',
            '缺少后置缓存变量',
        )

    def test_posterior_failure_preserves_original_failure(self):
        runtime = self.build_runtime('接口场景失败')

        runtime.run_case_posterior()

        self.assertEqual(
            runtime.api_case_result.error_message,
            '接口场景失败；用例后置处理失败：缺少后置缓存变量',
        )
