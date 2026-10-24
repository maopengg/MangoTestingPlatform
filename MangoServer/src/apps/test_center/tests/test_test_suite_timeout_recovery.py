from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService


class TestSuiteTimeoutRecoveryServiceTests(SimpleTestCase):
    def build_detail(self, case_type=TestCaseTypeEnum.API.value, retry=1):
        return SimpleNamespace(
            id=1,
            type=case_type,
            retry=retry,
            status=TaskEnum.PROCEED.value,
            push_time=timezone.now() - timedelta(minutes=31),
            error_message=None,
            success=0,
            fail=0,
            warning=0,
            summary_data=None,
            case_id=10,
            test_env=0,
            api_case_revision_id=None,
            api_case_release_id=None,
            test_suite_id=100,
            save=Mock(),
        )

    def test_failure_message_explains_timeout_reset_and_missing_result_for_all_types(self):
        expected_names = {
            TestCaseTypeEnum.API.value: 'API Case',
            TestCaseTypeEnum.UI.value: 'UI Case',
            TestCaseTypeEnum.PYTEST.value: 'Pytest Case',
        }
        for case_type, name in expected_names.items():
            with self.subTest(case_type=case_type):
                message = TestSuiteTimeoutRecoveryService.failure_message(case_type, 30, 4)
                self.assertIn(name, message)
                self.assertIn('系统超时重置并终止', message)
                self.assertIn('没有生成测试结果', message)

    def test_retry_message_explains_system_timeout_reset(self):
        message = TestSuiteTimeoutRecoveryService.retry_message(
            TestCaseTypeEnum.UI.value,
            30,
            2,
            3,
            4,
        )
        self.assertIn('UI Case', message)
        self.assertIn('超过30分钟且未回传结果', message)
        self.assertIn('第2次超时重置', message)
        self.assertIn('第3/4次执行', message)

    def test_reset_for_retry_sets_visible_system_timeout_message(self):
        detail = self.build_detail(retry=2)
        locked_queryset = Mock()
        locked_queryset.get.return_value = detail
        with patch.object(TestSuiteDetails.objects, 'select_for_update', return_value=locked_queryset):
            updated = TestSuiteTimeoutRecoveryService.reset_for_retry.__wrapped__(
                TestSuiteTimeoutRecoveryService,
                detail,
                30,
                4,
            )

        self.assertTrue(updated)
        self.assertEqual(detail.status, TaskEnum.STAY_BEGIN.value)
        self.assertIn('第2次超时重置', detail.error_message)
        self.assertIn('第3/4次执行', detail.error_message)

    def test_terminal_timeout_saves_empty_execution_record_and_metadata(self):
        detail = self.build_detail(TestCaseTypeEnum.PYTEST.value, retry=4)
        locked_queryset = Mock()
        locked_queryset.get.return_value = detail
        with patch.object(TestSuiteDetails.objects, 'select_for_update', return_value=locked_queryset), \
                patch.object(TestSuiteTimeoutRecoveryService, 'close_api_traces', return_value=None), \
                patch.object(TestSuiteTimeoutRecoveryService, 'save_empty_execution_record') as save_result:
            updated = TestSuiteTimeoutRecoveryService.fail_after_retries.__wrapped__(
                TestSuiteTimeoutRecoveryService,
                detail,
                30,
                4,
            )

        self.assertTrue(updated)
        self.assertEqual(detail.status, TaskEnum.FAIL.value)
        self.assertIn('没有生成测试结果', detail.error_message)
        self.assertFalse(detail.summary_data['meta']['termination']['has_test_result'])
        save_result.assert_called_once_with(detail, detail.error_message, None)

    def test_target_type_covers_api_ui_and_pytest(self):
        self.assertEqual(
            TestSuiteTimeoutRecoveryService.target_type(TestCaseTypeEnum.API.value),
            ExecutionResultService.TARGET_API_CASE,
        )
        self.assertEqual(
            TestSuiteTimeoutRecoveryService.target_type(TestCaseTypeEnum.UI.value),
            ExecutionResultService.TARGET_UI_CASE,
        )
        self.assertEqual(
            TestSuiteTimeoutRecoveryService.target_type(TestCaseTypeEnum.PYTEST.value),
            ExecutionResultService.TARGET_PYTEST_CASE,
        )

    def test_report_summary_keeps_timeout_termination_when_result_is_empty(self):
        termination = {
            'type': TestSuiteTimeoutRecoveryService.TERMINATION_TYPE,
            'has_test_result': False,
        }
        rows = [{
            'id': 1,
            'type': TestCaseTypeEnum.UI.value,
            'summary_data': {'children': None, 'meta': {'termination': termination}},
        }]
        with patch.object(TestSuiteExecutionResultService, 'get_payload_by_detail_id') as get_payload, \
                patch.object(TestSuiteExecutionResultService, 'save_detail_summary_by_id') as save_summary:
            TestSuiteExecutionResultService.attach_summary(rows)

        get_payload.assert_not_called()
        save_summary.assert_not_called()
        self.assertEqual(rows[0]['termination'], termination)
        self.assertFalse(rows[0]['has_result_data'])
