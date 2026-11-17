from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary
from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService as Retry
from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService as Infrastructure
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.task_center.services.workbench.report_infrastructure import ReportInfrastructureTodoService as Todos
from src.apps.test_center.selectors.infrastructure import ReportInfrastructureSelector as Selector


class PlatformBlockedResultsTests(SimpleTestCase):
    def test_renewed_lease_closes_trace_from_original_dispatch_not_renewal(self):
        claimed = timezone.now() - timedelta(minutes=3)
        renewed = claimed + timedelta(minutes=2)
        detail = SimpleNamespace(id=7, type=1, push_time=renewed, error_message='进程重启',
            summary_data={'children': [], 'meta': {
                'dispatch_started_at': claimed.isoformat(),
                'execution_control': {'phase': 'infrastructure_blocked', 'attempt': 2},
            }})
        with patch('src.apps.auto_api.services.execution_trace.recorder.'
                   'ApiCaseExecutionTraceRecorder.interrupt_report_attempt') as interrupt:
            Infrastructure.close_interrupted_trace(detail)
        interrupt.assert_called_once_with(7, claimed, '进程重启',
            detail.summary_data['meta']['execution_control'])

    def test_legacy_or_invalid_dispatch_time_keeps_current_attempt_boundary(self):
        pushed = timezone.now()
        for value in (None, '', 'invalid', '2026-99-99T00:00:00'):
            with self.subTest(value=value):
                detail = SimpleNamespace(id=7, type=1, push_time=pushed, error_message='中断',
                    summary_data={'children': [], 'meta': {'dispatch_started_at': value,
                        'execution_control': {'attempt': 2}}})
                with patch('src.apps.auto_api.services.execution_trace.recorder.'
                           'ApiCaseExecutionTraceRecorder.interrupt_report_attempt') as interrupt:
                    Infrastructure.close_interrupted_trace(detail)
                self.assertEqual(interrupt.call_args.args[1], pushed)

    def test_non_api_block_does_not_close_api_trace(self):
        with patch('src.apps.auto_api.services.execution_trace.recorder.'
                   'ApiCaseExecutionTraceRecorder.interrupt_report_attempt') as interrupt:
            Infrastructure.close_interrupted_trace(SimpleNamespace(type=2))
        interrupt.assert_not_called()

    def test_known_interruption_reason_is_saved_without_marking_business_failure(self):
        detail = SimpleNamespace(id=7, retry=2, status=TaskEnum.PROCEED.value,
            push_time=timezone.now(), summary_data=None, success=0, fail=0, warning=0, save=Mock())
        suite = SimpleNamespace(id=1, status=TaskEnum.PROCEED.value)
        reason = '执行进程已重启或被替换，本次执行未完成。请核查已发送请求及数据清理状态'
        with patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteDetails.objects') as details, \
                patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuite.objects') as suites, \
                patch('src.apps.test_center.services.reporting.test_suite.infrastructure.transaction.on_commit'), \
                patch.object(Infrastructure, 'close_interrupted_trace'), \
                patch.object(Infrastructure, '_finish_suite'):
            details.filter.return_value.values_list.return_value.get.return_value = 1
            details.select_for_update.return_value.get.return_value = detail
            suites.select_for_update.return_value.get.return_value = suite
            accepted = Infrastructure.block.__wrapped__(Infrastructure, 7, 2, [],
                expected_push_time=detail.push_time, interruption_reason=reason)
        self.assertTrue(accepted)
        self.assertIn(reason, detail.error_message)
        self.assertEqual(detail.failure_description, reason)
        self.assertEqual((detail.status, detail.fail), (TaskEnum.INFRASTRUCTURE_BLOCKED.value, 0))
        self.assertTrue(detail.summary_data['meta']['execution_control']['requires_review'])

    def row(self, status=6, **changes):
        return {'status': status, 'type': 1, 'case_sum': 1, 'success': 0, 'fail': 0,
                'warning': 0, 'is_excluded': False, 'summary_data': {}, **changes}

    def test_shared_status_keeps_existing_values(self):
        self.assertEqual([TaskEnum.FAIL.value, TaskEnum.SUCCESS.value, TaskEnum.STAY_BEGIN.value,
            TaskEnum.PROCEED.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value], list(range(6)))
        self.assertEqual(TaskEnum.INFRASTRUCTURE_BLOCKED.value, 6)

    def test_all_380_blocked_are_not_business_failures(self):
        counts = Summary.effective_summary_from_rows([self.row() for _ in range(380)])
        self.assertEqual((counts['total'], counts['blocked'], counts['fail']), (380, 380, 0))
        self.assertEqual(Summary.conclusion_status(6, counts, 380), 6)

    def test_legacy_phase_has_same_counts_without_rewriting_database(self):
        counts = Summary.effective_summary_from_rows([self.row(0, summary_data={
            'meta': {'execution_control': {'phase': 'infrastructure_blocked'}}})])
        self.assertEqual((counts['blocked'], counts['fail']), (1, 0))
        self.assertEqual(Summary.conclusion_status(0, counts, 1), 6)

    def test_mixed_report_preserves_real_business_failure(self):
        counts = Summary.effective_summary_from_rows([self.row(), self.row(0, fail=1), self.row(1, success=1)])
        self.assertEqual((counts['blocked'], counts['fail'], counts['success']), (1, 1, 1))
        self.assertEqual(Summary.conclusion_status(6, counts, 3), 0)

    def test_blocked_is_terminal_but_not_passed(self):
        counters = Summary.counter_data_from_rows([self.row()])
        self.assertEqual((counters['api_in_progress_case_sum'], counters['api_success'], counters['blocked']), (1, 0, 1))

    def test_successful_steps_do_not_turn_incomplete_result_into_pass(self):
        counts = Summary.effective_summary_from_rows([self.row(success=1)])
        self.assertEqual((counts['blocked'], counts['success'], counts['total']), (1, 0, 1))

    def test_excluded_blocks_do_not_pollute_effective_counts(self):
        counts = Summary.effective_summary_from_rows([self.row(is_excluded=True), self.row(1, success=1)])
        self.assertEqual((counts['blocked'], counts['excluded_count'], counts['total']), (0, 1, 1))

    def test_retry_requires_confirmation_not_diagnosis(self):
        detail = SimpleNamespace(id=7, retry=2, summary_data={'meta': {'execution_control': {
            'phase': 'infrastructure_blocked', 'attempt': 2, 'requires_review': True}}})
        with self.assertRaises(TestCenterError) as raised:
            Retry.ensure_infrastructure_reviewed(detail)
        self.assertEqual(raised.exception.code, 40107)
        with patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.cleanup_review_ready', return_value=True):
            Retry.ensure_infrastructure_reviewed(detail, confirmed=True)
        self.assertTrue(detail.summary_data['meta']['execution_control']['requires_review'])

    def test_confirmed_retry_still_checks_cleanup(self):
        detail = SimpleNamespace(id=7, retry=2, summary_data={'meta': {'execution_control': {
            'phase': 'infrastructure_blocked', 'attempt': 2, 'requires_review': True}}})
        with patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.cleanup_review_ready', return_value=False):
            with self.assertRaises(TestCenterError):
                Retry.ensure_infrastructure_reviewed(detail, confirmed=True)

    def test_coverage_sync_failure_cannot_erase_saved_result(self):
        with patch('src.apps.test_center.services.results.execution_result.transaction.atomic', return_value=nullcontext()), \
                patch('src.apps.auto_api.services.coverage.module_coverage.ModuleCoverageService.sync_api_case_execution_result', side_effect=OperationalError(1054, 'unknown column')), \
                patch('src.apps.test_center.services.results.execution_result.log.system.exception') as logged:
            ExecutionResultService.sync_coverage_result(1, 1, 10)
        logged.assert_called_once()

    def test_all_blocked_report_suppresses_normal_notification(self):
        sender = SendNotice.__new__(SendNotice)
        sender.test_suite = SimpleNamespace(id=7, save=Mock())
        with patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService.sync_todos'), \
                patch.object(Summary, 'counter_data', return_value={'blocked': 380, 'fail': 0}), \
                patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecutionService.complete_test_suite', return_value=False), \
                patch('src.apps.test_center.services.reporting.test_suite.send_notice.NoticeMain') as notice:
            self.assertFalse(sender.send_test_suite())
        notice.assert_not_called()
        sender.test_suite.save.assert_called_once()

    def test_380_blocks_create_one_product_todo_not_380(self):
        suite = SimpleNamespace(id=7, tasks_id=8, project_product_id=1, test_env=2,
            tasks=SimpleNamespace(name='回归'), project_product=SimpleNamespace(id=1), user_id=9)
        with patch.object(Selector, 'report', return_value=suite), \
                patch.object(Selector, 'details', return_value=[self.row() for _ in range(380)]), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.transaction.atomic', return_value=nullcontext()), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.transaction.on_commit') as commit, \
                patch('src.apps.test_center.models.ProjectProduct.objects.select_for_update'), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.WorkbenchTodo.objects.filter') as todos, \
                patch('src.apps.task_center.services.workbench.todo.WorkbenchTodoService._upsert') as upsert:
            todos.return_value.first.return_value = None
            Todos.sync(7)
        upsert.assert_called_once()
        payload = upsert.call_args.args[1]
        self.assertEqual(payload['details']['blocked_count'], 380)
        self.assertEqual(upsert.call_args.args[0], 'report-infrastructure:1:2:8')
        commit.assert_called_once()

    def test_pending_new_execution_does_not_close_todo(self):
        with patch.object(Selector, 'report', return_value=SimpleNamespace(id=7, tasks_id=8,
                project_product_id=1, test_env=2, status=3)), \
                patch.object(Selector, 'details', return_value=[self.row(3)]), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.WorkbenchTodo.objects.filter') as todos:
            Todos.sync(7)
        todos.assert_not_called()

    def test_business_failure_after_platform_recovery_can_close_platform_todo(self):
        suite = SimpleNamespace(id=9, tasks_id=8, project_product_id=1, test_env=2, status=0)
        with patch.object(Selector, 'report', return_value=suite), \
                patch.object(Selector, 'details', return_value=[self.row(0, fail=1)]), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.WorkbenchTodo.objects.filter') as todos:
            todos.return_value.first.return_value = None
            Todos.sync(9)
        todos.return_value.update.assert_called_once()
        self.assertEqual(todos.call_args.kwargs['source_id__lte'], 9)

    def test_partial_new_scope_does_not_close_old_fault(self):
        suite = SimpleNamespace(id=9, tasks_id=8, project_product_id=1, test_env=2, status=1)
        with patch.object(Selector, 'report', return_value=suite), \
                patch.object(Selector, 'details', return_value=[self.row(1, success=1)]), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.WorkbenchTodo.objects.filter') as todos:
            todos.return_value.first.return_value = SimpleNamespace(details={
                'execution_item_count': 380, 'scope_fingerprint': 'original-scope'})
            Todos.sync(9)
        todos.return_value.update.assert_not_called()

    def test_notification_failure_is_retryable_and_success_is_deduplicated(self):
        todo = SimpleNamespace(status=0, details={}, save=Mock())
        with patch('src.apps.task_center.services.workbench.report_infrastructure.transaction.atomic', return_value=nullcontext()), \
                patch('src.apps.task_center.services.workbench.report_infrastructure.WorkbenchTodo.objects.select_for_update') as todos, \
                patch('src.apps.task_center.services.workbench.todo.WorkbenchTodoService._notify_owner', return_value=False) as notify:
            todos.return_value.select_related.return_value.get.return_value = todo
            Todos.notify('fault')
            todo.save.assert_not_called()
            notify.return_value = True
            Todos.notify('fault')
            Todos.notify('fault')
        self.assertEqual(notify.call_count, 2)
        self.assertTrue(todo.details['owner_notified'])
        todo.save.assert_called_once()
