from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TestCaseTypeEnum, TaskEnum

from src.apps.test_center.services.test_suite.notice_details import ReportNoticeDetailsService


class NoticeDetailTests(SimpleTestCase):
    def detail(self, kind, **values):
        return SimpleNamespace(id=1, test_suite_id=10, case_id=100, case_name='测试用例', type=kind.value,
                               status=TaskEnum.FAIL.value, fail=1, error_message='用例错误提示', summary_data=None, **values)

    def test_api_uses_saved_interface_name_and_only_latest_failed_steps(self):
        detail = self.detail(TestCaseTypeEnum.API)
        rows = ReportNoticeDetailsService.detail_rows(detail, [
            {'status': 1, 'api_info_name': '成功接口'},
            {'status': 0, 'api_info_name': '失败接口', 'error_message': '期望200，实际500'},
        ], '任务组子任务')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].case_name, '测试用例')
        self.assertEqual(rows[0].target_name, '失败接口')
        self.assertEqual(rows[0].message, '期望200，实际500')
        self.assertEqual(rows[0].task_name, '任务组子任务')

    def test_successful_api_retry_replaces_old_failure(self):
        rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.API), [
            {'parameter_id': 1, 'status': 0, 'api_info_name': '旧失败接口'},
            {'parameter_id': 1, 'status': 1, 'api_info_name': '重试成功接口'},
            {'parameter_id': 2, 'status': 0, 'api_info_name': '仍失败接口'},
        ])
        self.assertEqual([row.target_name for row in rows], ['仍失败接口'])

    def test_ui_and_pytest_keep_failure_targets_without_generic_not_found_values(self):
        rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.UI), [
            {'status': 0, 'name': '填写账号', 'error_message': '输入框不可见'}])
        self.assertEqual(rows[0].target_name, '填写账号')
        rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.PYTEST), {
            'status': 'broken', 'fullName': 'example.py::test_read', 'statusDetails': {'message': 'fixture setup failed'}})
        self.assertEqual(rows[0].target_name, 'example.py::test_read')
        self.assertEqual(rows[0].message, 'fixture setup failed')

    def test_missing_steps_still_include_case_error_and_redact_credentials(self):
        detail = self.detail(TestCaseTypeEnum.API)
        detail.error_message = 'token=example-secret request failed'
        rows = ReportNoticeDetailsService.detail_rows(detail, None)
        self.assertNotIn('example-secret', rows[0].message)
        self.assertEqual(rows[0].target_name, '未记录接口名称')

    def test_summary_read_is_batched_and_does_not_load_payload_per_case(self):
        detail = self.detail(TestCaseTypeEnum.API)
        detail.summary_data = [{'status': 0, 'api_info_name': '保存接口', 'error_message': '断言失败'}]
        with patch('src.apps.test_center.services.test_suite.notice_details.ReportNoticeSelector.failed_details', return_value=[detail]), \
             patch('src.apps.test_center.services.test_suite.notice_details.TestSuiteExecutionResultService.result_map', return_value={}) as bulk:
            rows, note = ReportNoticeDetailsService.collect({10: '任务一'})
        bulk.assert_called_once_with([])
        self.assertEqual(len(rows), 1)
        self.assertFalse(note)

    def test_detail_read_failure_does_not_block_summary_notifications(self):
        with patch('src.apps.test_center.services.test_suite.notice_details.ReportNoticeSelector.failed_details', side_effect=RuntimeError('private')):
            rows, note = ReportNoticeDetailsService.collect({10: '任务一'})
        self.assertEqual(rows, [])
        self.assertIn('暂时不可用', note)
        self.assertNotIn('private', note)
