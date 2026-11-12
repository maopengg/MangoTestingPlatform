from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TestCaseTypeEnum, TaskEnum

from src.apps.test_center.services.reporting.test_suite.notice_details import ReportNoticeDetailsService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService


class NoticeDetailTests(SimpleTestCase):
    def test_interruption_notice_preserves_platform_reason_instead_of_partial_assertions(self):
        detail = self.detail(TestCaseTypeEnum.API)
        detail.summary_data = {'children': [], 'meta': {'execution_control': {
            'phase': 'infrastructure_blocked', 'requires_review': True}}}
        rows = ReportNoticeDetailsService.detail_rows(detail, [{'status': 0, 'error_message': 'partial failure'}])
        self.assertEqual(len(rows), 1)
        self.assertIn('非业务断言失败', rows[0].target_name)
        self.assertIn('复核原请求及清理状态', rows[0].message)
        self.assertNotIn('partial failure', rows[0].message)

    def test_two_failed_cases_with_thirty_unexecuted_steps_produce_two_rows(self):
        import json
        from src.apps.system.services.notice import ReportFailureRenderer

        first = self.detail(TestCaseTypeEnum.API)
        first.summary_data = [{'parameter_id': 1, 'status': 0, 'api_info_name': '查询审批列表', 'error_message': '业务码断言失败'}]
        second = self.detail(TestCaseTypeEnum.API)
        second.id, second.case_id, second.case_name = 2, 101, '创建问答消息'
        second.summary_data = [{'parameter_id': 2, 'status': 0, 'api_info_name': '查询会话历史', 'error_message': 'JSON一致断言失败'}]
        second.summary_data.extend({'parameter_id': i, 'status': TaskEnum.WARNING.value, 'main_status': 0,
                                    'api_info_name': '发送对话消息', 'error_message': TestSuiteExecutionResultService.SKIP_MESSAGE}
                                   for i in range(3, 33))
        with patch('src.apps.test_center.services.reporting.test_suite.notice_details.ReportNoticeSelector.failed_details', return_value=[first, second]), \
                patch.object(TestSuiteExecutionResultService, 'result_map', return_value={}):
            rows, note = ReportNoticeDetailsService.collect({10: '测试回归'})
        self.assertEqual(len(rows), 2)
        self.assertFalse(note)
        card = ReportFailureRenderer.feishu({'elements': []}, rows)
        self.assertIn('失败明细（共 2 条）', json.dumps(card, ensure_ascii=False))
        self.assertEqual(len(next(item for item in card['elements'] if item['tag'] == 'table')['rows']), 2)

    def test_multiple_real_failures_in_one_case_are_combined_not_duplicated(self):
        for kind in (TestCaseTypeEnum.API, TestCaseTypeEnum.UI):
            with self.subTest(kind=kind):
                rows = ReportNoticeDetailsService.detail_rows(self.detail(kind), [
                    {'parameter_id': 1, 'status': 0, 'name': '步骤一', 'api_info_name': '步骤一', 'error_message': '错误一'},
                    {'parameter_id': 2, 'status': 0, 'name': '步骤二', 'api_info_name': '步骤二', 'error_message': '错误二'},
                ])
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].target_name, '步骤一\n步骤二')
                self.assertIn('错误一', rows[0].message)
                self.assertIn('错误二', rows[0].message)

    def test_feishu_keeps_real_failure_but_omits_unexecuted_following_steps(self):
        import json
        from copy import deepcopy
        from src.apps.system.services.notice import ReportFailureRenderer

        data = [{'parameter_id': 1, 'status': 0, 'api_info_name': '查询会话历史', 'error_message': 'JSON一致断言失败'}]
        data.extend({'parameter_id': i, 'status': status, 'main_status': 0, 'api_info_name': '发送对话消息',
                     'error_message': TestSuiteExecutionResultService.SKIP_MESSAGE}
                    for i, status in enumerate((TaskEnum.WARNING.value, TaskEnum.FAIL.value, 'failed'), start=2))
        original = deepcopy(data)
        rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.API), data)
        self.assertEqual([row.target_name for row in rows], ['查询会话历史'])
        card = json.dumps(ReportFailureRenderer.feishu({'elements': []}, rows), ensure_ascii=False)
        self.assertIn('查询会话历史', card)
        self.assertNotIn('发送对话消息', card)
        self.assertNotIn(TestSuiteExecutionResultService.SKIP_MESSAGE, card)
        self.assertEqual(data, original)

    def test_all_unexecuted_steps_do_not_reappear_as_generic_case_failure(self):
        for status in (TaskEnum.WARNING.value, TaskEnum.FAIL.value):
            with self.subTest(status=status):
                rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.API), [
                    {'status': status, 'main_status': 0, 'error_message': TestSuiteExecutionResultService.SKIP_MESSAGE}])
                self.assertEqual(rows, [])

    def test_missing_steps_with_unexecuted_case_error_are_not_notified(self):
        detail = self.detail(TestCaseTypeEnum.API)
        detail.error_message = TestSuiteExecutionResultService.SKIP_MESSAGE
        self.assertEqual(ReportNoticeDetailsService.detail_rows(detail, None), [])

    def test_latest_skipped_retry_does_not_resurrect_old_failure(self):
        rows = ReportNoticeDetailsService.detail_rows(self.detail(TestCaseTypeEnum.API), [
            {'parameter_id': 1, 'status': 0, 'api_info_name': '旧失败', 'error_message': '断言失败'},
            {'parameter_id': 1, 'status': TaskEnum.WARNING.value, 'error_message': TestSuiteExecutionResultService.SKIP_MESSAGE},
        ])
        self.assertEqual(rows, [])

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
        with patch('src.apps.test_center.services.reporting.test_suite.notice_details.ReportNoticeSelector.failed_details', return_value=[detail]), \
             patch('src.apps.test_center.services.reporting.test_suite.notice_details.TestSuiteExecutionResultService.result_map', return_value={}) as bulk:
            rows, note = ReportNoticeDetailsService.collect({10: '任务一'})
        bulk.assert_called_once_with([])
        self.assertEqual(len(rows), 1)
        self.assertFalse(note)

    def test_detail_read_failure_does_not_block_summary_notifications(self):
        with patch('src.apps.test_center.services.reporting.test_suite.notice_details.ReportNoticeSelector.failed_details', side_effect=RuntimeError('private')):
            rows, note = ReportNoticeDetailsService.collect({10: '任务一'})
        self.assertEqual(rows, [])
        self.assertIn('暂时不可用', note)
        self.assertNotIn('private', note)
