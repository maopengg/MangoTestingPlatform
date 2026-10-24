from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum
from rest_framework.test import APIRequestFactory, force_authenticate

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.api.views.task_group import ScheduledTaskGroupViews
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService


class TaskGroupNoticeResendTests(SimpleTestCase):
    def test_excluded_original_failure_resends_clean_group_report(self):
        self.fires[0].test_suite.status = TaskEnum.FAIL.value
        summary = dict(case_sum=0, success=0, fail=0, warning=0, excluded_count=10)
        with patch('src.apps.task_center.services.scheduling.task_group_execution.TestSuiteSummaryService.counter_data', return_value=summary):
            report = ScheduledTaskGroupExecutionService._build_report(self.execution, self.fires)
        self.assertEqual(report.failed_task_count, 0)
        self.assertEqual(report.excluded_count, 10)
        self.assertEqual(report.success_rate, 100)
        self.assertEqual(report.children[0].result, '成功')
        from src.apps.task_center.services.scheduling.task_group_notice import TaskGroupNoticeBuilder
        self.assertIn('已排除用例', TaskGroupNoticeBuilder(report).build_wechat_markdown())

    def setUp(self):
        self.execution = SimpleNamespace(
            id=68, expected_count=2, notice_status=TestSuiteNoticeEnum.SENT.value,
            notice_group_id=9, is_notice=0, fail_notice=1, save=MagicMock(),
            task_group_name='示例巡检', test_env=0, planned_at=timezone.now(),
            create_time=timezone.now(),
            finished_at=timezone.now(),
            project_product=SimpleNamespace(name='示例产品', project=SimpleNamespace(name='示例项目')),
        )
        now = timezone.now()
        self.fires = [SimpleNamespace(
            id=1, test_suite_id=9001, task_name='子任务一',
            status=ScheduleFireStatusEnum.DISPATCHED.value,
            test_suite=SimpleNamespace(status=TaskEnum.SUCCESS.value, create_time=now, update_time=now),
        ), SimpleNamespace(
            id=2, test_suite_id=None, task_name='未生成报告的任务',
            status=ScheduleFireStatusEnum.SKIPPED.value,
        )]
        patches = {
            'atomic': patch('src.apps.task_center.services.scheduling.task_group_execution.transaction.atomic',
                            side_effect=nullcontext),
            'executions': patch(
                'src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecution.objects'),
            'fires': patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduleFire.objects'),
            'details': patch('src.apps.task_center.services.scheduling.task_group_execution.TestSuiteDetails.objects'),
            'notice': patch('src.apps.task_center.services.scheduling.task_group_execution.NoticeMain'),
        }
        self.mocks = {}
        for name, item in patches.items():
            self.mocks[name] = item.start()
            self.addCleanup(item.stop)
        self.mocks[
            'executions'].select_for_update.return_value.select_related.return_value.filter.return_value.first.return_value = self.execution
        self.mocks['fires'].filter.return_value.select_related.return_value.order_by.return_value = self.fires
        self.mocks['details'].filter.return_value.exclude.return_value.exists.return_value = False

    def test_resend_recomputes_current_results_even_success_and_notice_disabled(self):
        self.fires[0].status = ScheduleFireStatusEnum.FAIL.value
        with patch('src.apps.task_center.services.scheduling.task_group_execution.TestSuiteSummaryService.counter_data',
                   return_value={'case_sum': 10, 'success': 10, 'fail': 0, 'warning': 0, 'api_case_sum': 10}):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        report = self.mocks['notice'].return_value.notice_task_group.call_args.args[0]
        self.assertEqual(report.success, 10)
        self.assertEqual(report.fail, 0)
        self.assertEqual(report.task_count, 1)
        self.assertEqual(report.children[0].test_suite_id, 9001)
        self.assertEqual(report.children[0].result, '成功')
        self.mocks['notice'].assert_called_once_with(9)
        self.assertEqual(self.mocks['executions'].filter.return_value.update.call_args.kwargs['notice_status'],
                         TestSuiteNoticeEnum.SENT.value)

    def test_current_failure_counts_produce_failed_child_even_with_stale_success_status(self):
        with patch('src.apps.task_center.services.scheduling.task_group_execution.TestSuiteSummaryService.counter_data',
                   return_value={'case_sum': 10, 'success': 9, 'fail': 1, 'warning': 0}):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        report = self.mocks['notice'].return_value.notice_task_group.call_args.args[0]
        self.assertEqual(report.failed_task_count, 1)
        self.assertEqual(report.children[0].result, '失败')
        self.assertEqual(report.fail, 1)

    def test_running_retry_detail_blocks_resend_even_if_fire_is_terminal(self):
        self.fires[0].status = ScheduleFireStatusEnum.FAIL.value
        self.mocks['details'].filter.return_value.exclude.return_value.exists.return_value = True
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.execution.save.assert_not_called()
        self.mocks['notice'].assert_not_called()

    def test_running_suite_blocks_resend(self):
        self.fires[0].test_suite.status = TaskEnum.PROCEED.value
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.mocks['notice'].assert_not_called()

    def test_concurrent_send_is_rejected_and_auto_finalize_does_not_overwrite_it(self):
        self.execution.notice_status = TestSuiteNoticeEnum.SENDING.value
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.assertIsNone(ScheduledTaskGroupExecutionService._claim_notice(68))
        self.execution.save.assert_not_called()

    def test_wrong_group_missing_notice_group_and_empty_reports_are_rejected(self):
        manager = self.mocks['executions'].select_for_update.return_value.select_related.return_value.filter
        manager.return_value.first.return_value = None
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(3, 68)
        manager.assert_called_with(id=68, task_group_id=3)
        manager.return_value.first.return_value = self.execution
        self.execution.notice_group_id = None
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.execution.notice_group_id = 9
        self.fires[:] = [self.fires[1]]
        self.execution.expected_count = 1
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.mocks['notice'].assert_not_called()

    def test_send_failure_restores_previous_status_without_automatic_resend(self):
        self.execution.notice_status = TestSuiteNoticeEnum.EXPIRED.value
        self.mocks['notice'].return_value.notice_task_group.side_effect = RuntimeError('send failed')
        with patch.object(ScheduledTaskGroupExecutionService, '_build_report', return_value=MagicMock()):
            with self.assertRaises(RuntimeError):
                ScheduledTaskGroupExecutionService.resend_notice(2, 68)
        self.assertEqual(self.mocks['executions'].filter.return_value.update.call_args.kwargs['notice_status'],
                         TestSuiteNoticeEnum.EXPIRED.value)

    def test_endpoint_checks_product_scope_and_passes_explicit_batch(self):
        view = ScheduledTaskGroupViews.as_view({'post': 'resend_notice'})
        request = APIRequestFactory().post('/api/system/tasks/groups/notice/resend',
                                           {'id': 2, 'execution_id': 68}, format='json')
        force_authenticate(request, user=SimpleNamespace(user_obj=SimpleNamespace(id=4)))
        with (
            patch.object(ScheduledTaskGroupViews, '_group') as scope,
            patch.object(ScheduledTaskGroupExecutionService, 'resend_notice') as resend,
            patch('src.apps.user.middleware.permission.PermissionMenuService.is_effective_super_admin',
                  return_value=True),
        ):
            response = view(request)
        self.assertEqual(response.data['code'], 200)
        scope.assert_called_once()
        self.assertEqual(scope.call_args.args[1], 2)
        resend.assert_called_once_with(2, 68)
