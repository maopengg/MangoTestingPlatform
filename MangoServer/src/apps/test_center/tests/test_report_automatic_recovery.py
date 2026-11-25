from contextlib import ExitStack, nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
from src.apps.test_center.enums.reporting import ReportRecoveryActionEnum as Action, ReportRecoveryCauseEnum as Cause, ReportExecutionPhaseEnum as Phase
from src.apps.test_center.schemas.infrastructure import ReportRecoveryControl
from src.apps.test_center.services.reporting.test_suite.recovery import ReportRecoveryService as Recovery
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary
from src.apps.test_center.models import TestSuite, TestSuiteDetails, ExecutionResult
from src.apps.monitoring.models import SystemErrorEvent
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService


class ReportAutomaticRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.suite = SimpleNamespace(id=2, status=3, retained_summary=None)
        self.detail = SimpleNamespace(id=7, test_suite_id=2, retry=1, type=1, case_sum=4,
            status=3, success=0, fail=0, warning=0, error_message='', failure_reason='', failure_description='',
            push_time=self.now - timedelta(minutes=1), save=Mock(),
            summary_data={'children': None, 'meta': {'api_count_by_scenario': True}})
        self.control = ReportRecoveryControl(attempt=1, cause=Cause.WORKER_REPLACED, action=Action.RETRY,
            observed_at=self.now, next_check_at=self.now, deadline_at=self.now + timedelta(minutes=5), owner_ended=True)
        Recovery.put(self.detail, self.control)

    def harness(self, *, ready=True, restored=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.transaction.atomic',
            side_effect=lambda *args, **kwargs: args[0] if args and callable(args[0]) else nullcontext()))
        stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.timezone.now', return_value=self.now))
        suites = stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.TestSuite.objects'))
        suites.select_for_update.return_value.filter.return_value.first.return_value = self.suite
        suites.select_for_update.return_value.get.return_value = self.suite
        details = stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.TestSuiteDetails.objects'))
        details.filter.return_value.values_list.return_value.first.return_value = self.suite.id
        details.select_for_update.return_value.filter.return_value.first.return_value = self.detail
        details.select_for_update.return_value.get.return_value = self.detail
        stack.enter_context(patch.object(Recovery, 'owner_ended', return_value=True))
        stack.enter_context(patch.object(Recovery, 'restore_result', return_value=restored))
        resource_ready = stack.enter_context(patch.object(Recovery, 'resources_ready', return_value=ready))
        stack.enter_context(patch('src.apps.auto_api.selectors.resource_cleanup.ApiResourceCleanupSelector.pending_for_attempt', return_value=[]))
        stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService.close_interrupted_trace'))
        finished = stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService._finish_suite'))
        event = stack.enter_context(patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEventService.record_report_recovery_failure'))
        stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.SystemConfigService.get_test_suite_timeout_max_attempts', return_value=4))
        return resource_ready, finished, event

    def test_all_fourteen_infrastructure_codes_have_explicit_recovery_policy(self):
        policies = {
            Action.FAIL: (34184, 34175, 34187, 34193),
            Action.RETRY: (34185, 34186, 34173),
            Action.RECOVER: (34191, 34192, 34174, 34176, 34188, 34189, 34190),
        }
        for action, codes in policies.items():
            for code in codes:
                with self.subTest(code=code):
                    self.assertEqual(Recovery.decide(Cause.DATASOURCE,
                        [DatasourceInfrastructureIssue(code=code, message='模拟故障')]), action)
        self.assertEqual(Recovery.decide(Cause.CODE_BUG, []), Action.FAIL)
        self.assertEqual(Recovery.decide(Cause.WORKER_REPLACED, []), Action.RETRY)
        self.assertEqual(Recovery.decide(Cause.LEASE_EXPIRED, []), Action.RECOVER)
        self.assertEqual(Recovery.decide(Cause.DATASOURCE,
            [DatasourceInfrastructureIssue(code=99999, message='未知类别')]), Action.FAIL)

    def test_worker_replacement_automatically_requeues_without_resetting_attempt(self):
        ready, finished, event = self.harness()
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual(self.detail.status, TaskEnum.STAY_BEGIN.value)
        self.assertEqual(self.detail.retry, 1)
        self.assertIsNone(self.detail.push_time)
        self.assertEqual(self.detail.summary_data['meta']['recovery_history'][0]['outcome'], 'retry_queued')
        self.assertNotIn('execution_control', self.detail.summary_data['meta'])
        finished.assert_not_called(); event.assert_not_called()

    def test_completed_result_is_restored_without_rerunning_case(self):
        _, finished, event = self.harness(restored=(1, {'success': 4, 'fail': 0, 'warning': 0}, [{'status': 1}]))
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual((self.detail.status, self.detail.success, self.detail.retry), (1, 4, 1))
        self.assertEqual(self.detail.summary_data['meta']['recovery_history'][0]['outcome'], 'result_restored')
        finished.assert_called_once(); event.assert_not_called()

    def test_unconfirmed_resources_wait_and_do_not_replay_or_send_final_notice(self):
        _, finished, event = self.harness(ready=False)
        self.assertFalse(Recovery.process_one(7))
        control = Recovery.read(self.detail.summary_data)
        self.assertEqual((self.detail.status, control.checks), (3, 1))
        self.assertGreater(control.next_check_at, self.now)
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(Recovery.read(self.detail.summary_data).checks, 1)
        finished.assert_not_called(); event.assert_not_called()

    def test_deadline_and_retry_budget_exhaustion_record_failure_once(self):
        _, finished, event = self.harness()
        self.detail.retry = self.control.attempt = 4
        Recovery.put(self.detail, self.control)
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual((self.detail.status, self.detail.fail), (0, 4))
        self.assertEqual(Recovery.read(self.detail.summary_data).reason.value, 'retry_budget_exhausted')
        self.assertTrue(Recovery.read(self.detail.summary_data).exception_recorded)
        self.assertFalse(Recovery.process_one(7))
        event.assert_called_once(); finished.assert_called_once()

    def test_unrecoverable_timeout_finalizes_and_records_system_exception(self):
        _, _, event = self.harness(ready=False)
        self.control.deadline_at = self.now - timedelta(seconds=1)
        Recovery.put(self.detail, self.control)
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual(self.detail.status, 0)
        self.assertEqual(event.call_args.kwargs['reason'], 'recovery_deadline_exhausted')

    def test_bug_finishes_without_requeue_and_expected_failure_is_explicitly_reported(self):
        _, finished, event = self.harness()
        with patch('src.apps.test_center.services.reporting.test_suite.recovery.SystemConfigService.get_test_suite_stuck_reset_minutes', return_value=5):
            control = Recovery.begin_locked(self.suite, self.detail,
                [DatasourceInfrastructureIssue(code=34184, message='错误配置')], Cause.DATASOURCE)
        self.assertEqual((control.action, self.detail.status, self.detail.retry), (Action.FAIL, 0, 1))
        event.assert_called_once(); finished.assert_called_once()
        self.assertEqual(event.call_args.kwargs['codes'], [34184])

    def test_system_exception_record_failure_keeps_pending_registration_for_compensation(self):
        _, _, event = self.harness()
        event.side_effect = RuntimeError('mock persistence unavailable')
        self.detail.retry = self.control.attempt = 4
        Recovery.put(self.detail, self.control)
        Recovery.process_one(7)
        self.assertEqual(self.detail.status, 0)
        self.assertFalse(Recovery.read(self.detail.summary_data).exception_recorded)
        event.side_effect = None
        self.now += timedelta(seconds=61)
        with patch('src.apps.test_center.services.reporting.test_suite.recovery.timezone.now', return_value=self.now):
            Recovery.process_one(7)
        self.assertTrue(Recovery.read(self.detail.summary_data).exception_recorded)
        self.assertEqual(self.detail.retry, 4)

    def test_old_attempt_and_user_stop_fence_automatic_recovery(self):
        ready, finished, event = self.harness()
        ready.side_effect = lambda *a: setattr(self.detail, 'retry', 2) or True
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(self.detail.retry, 2)
        self.assertEqual(self.detail.status, 3)
        self.suite.status = 5
        self.assertFalse(Recovery.process_one(7))
        finished.assert_not_called(); event.assert_not_called()

    def test_legacy_markers_are_read_only_and_do_not_auto_release(self):
        _, _, event = self.harness()
        self.detail.summary_data = {'meta': {'execution_control': {'phase': 'infrastructure_blocked', 'attempt': 1}}}
        self.assertIsNone(Recovery.read(self.detail.summary_data))
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(self.detail.status, 3)
        event.assert_not_called()

    def test_legacy_counts_display_as_failure_without_mutating_snapshot(self):
        previous = {'success': 2, 'fail': 0, 'blocked': 3, 'api_fail': 0, 'api_blocked': 3}
        current = Summary.public_counts(previous)
        self.assertEqual((current['fail'], current['blocked'], current['api_fail']), (3, 0, 3))
        self.assertEqual(previous['blocked'], 3)
        self.assertEqual(Summary.public_status(6), 0)

    def test_saved_result_waits_until_original_resources_are_confirmed(self):
        _, finished, event = self.harness(ready=False, restored=(1, {'success': 4, 'fail': 0, 'warning': 0}, []))
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(self.detail.status, TaskEnum.PROCEED.value)
        finished.assert_not_called()
        event.assert_not_called()

    def test_unknown_recovery_bug_stops_and_records_system_exception(self):
        ready, _, event = self.harness()
        ready.side_effect = TypeError('simulated internal failure')
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual(self.detail.status, TaskEnum.FAIL.value)
        self.assertEqual(event.call_args.kwargs['reason'], 'internal_recovery_error')

    def test_platform_database_unavailable_waits_without_replaying_case(self):
        from django.db import OperationalError
        ready, finished, event = self.harness()
        ready.side_effect = OperationalError('simulated unavailable database')
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(self.detail.status, TaskEnum.PROCEED.value)
        finished.assert_not_called()
        event.assert_not_called()

    def test_invalid_new_control_fails_closed_but_legacy_is_not_rewritten(self):
        _, _, event = self.harness()
        self.detail.summary_data['meta']['execution_control']['cause'] = 'invalid'
        self.assertTrue(Recovery.process_one(7))
        self.assertEqual(self.detail.status, TaskEnum.FAIL.value)
        self.assertEqual(event.call_args.kwargs['reason'], 'invalid_recovery_control')

    def test_owner_finished_note_preserves_attempt_and_rejects_stopped_detail(self):
        self.harness()
        self.assertTrue(Recovery.note_owner_ended.__wrapped__(Recovery, 7, 1))
        self.assertTrue(Recovery.read(self.detail.summary_data).owner_ended)
        self.assertEqual(self.detail.retry, 1)
        self.detail.status = TaskEnum.STOPPED.value
        self.assertFalse(Recovery.note_owner_ended.__wrapped__(Recovery, 7, 1))

    def test_http_and_mcp_status_options_share_the_same_public_catalog(self):
        from src.apps.system.services.catalog.enum_catalog import EnumCatalogService
        from src.interfaces.mcp.tools.report.test_report import _report_status_options, _status_title
        options = EnumCatalogService.task_status_options()
        self.assertEqual(_report_status_options(), [{'value': item['key'], 'label': item['title']} for item in options])
        self.assertEqual(_status_title(6), _status_title(0))

    def test_unreadable_known_result_waits_and_never_requeues_business(self):
        original_restore = Recovery.restore_result
        _, finished, event = self.harness()
        saved = SimpleNamespace(id=99, status=1, result_checksum=None)
        with patch.object(Recovery, 'restore_result', side_effect=original_restore), patch(
                'src.apps.test_center.selectors.report_recovery.ReportRecoverySelector.completed_result', return_value=saved), patch(
                'src.apps.test_center.services.results.execution_result.ExecutionResultService.load_result_data', return_value=None):
            self.assertFalse(Recovery.process_one(7))
        control = Recovery.read(self.detail.summary_data)
        self.assertEqual((self.detail.status, self.detail.retry, control.result_expected), (3, 1, True))
        self.assertEqual(control.reason.value, 'result_unavailable')
        finished.assert_not_called(); event.assert_not_called()

    def test_unknown_result_expected_does_not_requeue_even_if_resource_check_is_ready(self):
        self.harness()
        self.control.result_expected = True
        Recovery.put(self.detail, self.control)
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual((self.detail.status, self.detail.retry), (3, 1))

    def test_new_result_evidence_invalidates_an_inflight_recovery_check(self):
        ready, finished, event = self.harness()
        def callback(*args):
            latest = Recovery.read(self.detail.summary_data)
            latest.result_expected, latest.result_id = True, 99
            latest.checks += 1
            Recovery.put(self.detail, latest)
            return True
        ready.side_effect = callback
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual(self.detail.status, 3)
        self.assertEqual(Recovery.read(self.detail.summary_data).result_id, 99)
        finished.assert_not_called(); event.assert_not_called()

    def test_worker_result_unknown_marker_arriving_during_scan_prevents_requeue(self):
        ready, finished, event = self.harness()
        def mark_unknown(*args):
            latest = Recovery.read(self.detail.summary_data)
            latest.result_expected = True
            Recovery.put(self.detail, latest)
            return True
        ready.side_effect = mark_unknown
        self.assertFalse(Recovery.process_one(7))
        self.assertEqual((self.detail.status, self.detail.retry), (3, 1))
        finished.assert_not_called(); event.assert_not_called()

    def test_unknown_io_is_not_a_confirmed_bug_but_programming_errors_are(self):
        for error in (OSError(), TimeoutError(), RuntimeError()):
            self.assertFalse(Recovery.is_confirmed_code_bug(error))
        for error in (TypeError(), AttributeError(), NameError(), KeyError()):
            self.assertTrue(Recovery.is_confirmed_code_bug(error))

    def test_worker_file_error_requires_result_recovery_instead_of_code_bug_or_replay(self):
        from concurrent.futures import Future
        from src.processes.api_worker.runner import ApiWorkerRunner
        from src.apps.test_center.exceptions import ExecutionResultStorageError, EXECUTION_RESULT_STORAGE_UNAVAILABLE
        for error in (OSError('simulated unavailable storage'),
                      ExecutionResultStorageError(EXECUTION_RESULT_STORAGE_UNAVAILABLE), TypeError('simulated bug')):
            with self.subTest(error=type(error).__name__):
                future = Future(); future.set_exception(error)
                with patch('src.apps.task_center.services.execution.worker_recovery.ApiWorkerRecoveryService.finish_unreported') as finish:
                    ApiWorkerRunner.settle_finished({future: SimpleNamespace(test_suite_details=7, attempt=1)}, [future])
                self.assertEqual(finish.call_args.kwargs['code_bug'], isinstance(error, TypeError))
                self.assertEqual(finish.call_args.kwargs.get('result_expected', False), not isinstance(error, TypeError))

    def test_file_storage_boundary_raises_sanitized_typed_error(self):
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        from src.apps.test_center.exceptions import ExecutionResultStorageError
        with patch('src.apps.test_center.services.results.execution_result.default_storage.save',
                   side_effect=OSError('private storage credentials')):
            with self.assertRaises(ExecutionResultStorageError) as raised:
                ExecutionResultService.save_result_file([], target_type='api_case', target_id=11)
        self.assertNotIn('private', str(raised.exception))

    def test_recovery_is_registered_as_a_bounded_minute_scheduler_job(self):
        from src.apps.task_center.services.scheduling.system_job import SystemJobService
        from src.processes.scheduler.system_jobs import SchedulerSystemJobService
        job = next(job for job in SystemJobService.JOBS if job.key == 'recover_api_report_executions')
        self.assertEqual(job.cron, '* * * * *')
        self.assertEqual(job.handler, SchedulerSystemJobService.recover_api_report_executions)
        with patch.object(Recovery, 'process_due', return_value=2) as process, patch(
                'src.apps.auto_api.services.execution_trace.report_reconciliation.ApiReportTraceReconciliationService.reconcile',
                return_value=1) as reconcile:
            result = SchedulerSystemJobService.recover_api_report_executions.__wrapped__(SchedulerSystemJobService)
        self.assertEqual(result, {'recovered_count': 2, 'trace_reconciled_count': 1})
        process.assert_called_once_with(limit=100)
        reconcile.assert_called_once_with(limit=100)


class ReportRecoveryPersistenceTests(SimpleTestCase):
    """真实 ORM/事务在独立内存连接上运行，不创建 Django 测试库、不执行迁移。"""

    def setUp(self):
        self.original = connections['default']
        self.memory = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'TIME_ZONE': None,
            'CONN_HEALTH_CHECKS': False, 'CONN_MAX_AGE': 0, 'OPTIONS': {}, 'AUTOCOMMIT': True,
        }, alias='report-recovery-only-memory')
        connections['report-recovery-only-memory'] = self.memory
        self.addCleanup(self.restore_connection)
        self.memory.disable_constraint_checking()
        with self.memory.schema_editor() as editor:
            for model in (TestSuite, TestSuiteDetails, ExecutionResult, SystemErrorEvent):
                editor.create_model(model)
        self.memory.disable_constraint_checking()
        connections['default'] = self.memory
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.SystemConfigService.get_test_suite_stuck_reset_minutes', return_value=5))
        self.stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.recovery.SystemConfigService.get_test_suite_timeout_max_attempts', return_value=4))
        self.stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService.close_interrupted_trace'))
        self.stack.enter_context(patch.object(Recovery, 'resources_ready', return_value=True))
        self.stack.enter_context(patch('src.apps.auto_api.selectors.resource_cleanup.ApiResourceCleanupSelector.pending_for_attempt', return_value=[]))
        self.notice = self.stack.enter_context(patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService.finish_notice'))
        self.record_event = SystemErrorEventService.record_report_recovery_failure
        self.event = self.stack.enter_context(patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEventService.record_report_recovery_failure'))
        self.now = timezone.now()
        self.suite = TestSuite.objects.create(id=2, project_product_id=1, user_id=1, test_env=0, status=3, is_notice=0)
        self.detail = TestSuiteDetails.objects.create(id=7, test_suite=self.suite, type=1,
            project_product_id=1, test_env=0, case_id=11, status=3, retry=1, case_sum=4,
            push_time=self.now - timedelta(seconds=1),
            summary_data={'children': None, 'meta': {'api_count_by_scenario': True, 'api_scene_count': 4}})

    def restore_connection(self):
        connections['default'] = self.original
        del connections['report-recovery-only-memory']
        self.memory.close()

    def begin(self, cause=Cause.WORKER_REPLACED, issues=()):
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        return TestSuiteInfrastructureService.block(7, 1, list(issues), cause=cause)

    def tick(self):
        with patch('src.apps.test_center.services.reporting.test_suite.recovery.timezone.now', return_value=self.now + timedelta(seconds=3)):
            return Recovery.process_due()

    def test_restart_is_persisted_then_requeued_exactly_once_without_final_notice(self):
        self.assertTrue(self.begin())
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, Recovery.read(self.detail.summary_data).owner_ended), (3, True))
        self.assertEqual(self.tick(), 1)
        self.assertEqual(self.tick(), 0)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (2, 1))
        self.assertIn('recovery_history', self.detail.summary_data['meta'])
        self.notice.assert_not_called(); self.event.assert_not_called()

    def test_original_completed_result_is_restored_and_notice_runs_after_commit(self):
        ExecutionResult.objects.create(source_type='report', target_type='api_case', target_id=11,
            test_suite=self.suite, test_suite_detail=self.detail, status=1,
            result_data=[{'id': value, 'status': 1} for value in range(4)])
        self.begin()
        self.assertEqual(self.tick(), 1)
        self.detail.refresh_from_db(); self.suite.refresh_from_db()
        self.assertEqual((self.detail.status, self.suite.status, self.detail.success), (1, 1, 4))
        self.notice.assert_called_once_with(2)
        self.event.assert_not_called()

    def test_non_retryable_failure_is_terminal_and_registered_once(self):
        self.begin(Cause.CODE_BUG)
        self.detail.refresh_from_db(); self.suite.refresh_from_db()
        self.assertEqual((self.detail.status, self.suite.status, self.detail.fail), (0, 0, 4))
        self.assertTrue(Recovery.read(self.detail.summary_data).exception_recorded)
        self.assertEqual(self.tick(), 0)
        self.event.assert_called_once()
        self.notice.assert_called_once_with(2)

    def test_system_exception_and_dedup_marker_are_actually_persisted(self):
        self.event.side_effect = self.record_event
        self.begin(Cause.CODE_BUG)
        self.assertEqual(self.tick(), 0)
        event = SystemErrorEvent.objects.get()
        self.assertEqual(event.exception_type, 'ReportRecoveryFailure')
        self.assertEqual(event.request_path, 'report/2/detail/7/attempt/1')
        self.assertEqual(event.count, 1)
        self.detail.refresh_from_db()
        self.assertTrue(Recovery.read(self.detail.summary_data).exception_recorded)

    def test_mcp_detail_counts_fold_historical_blocks_in_one_group_query(self):
        from src.interfaces.mcp.tools.report.test_report import _status_counts
        TestSuiteDetails.objects.filter(id=7).update(status=6)
        counts = _status_counts(TestSuiteDetails.objects.filter(test_suite_id=2))
        self.assertEqual((counts['fail'], counts['blocked'], counts['success']), (1, 0, 0))

    def test_existing_result_file_unavailable_then_restored_without_replaying(self):
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        payload = [{'id': index, 'status': 1} for index in range(4)]
        ExecutionResult.objects.create(source_type='report', target_type='api_case', target_id=11,
            test_suite=self.suite, test_suite_detail=self.detail, status=1, result_object_key='example/result.json',
            result_checksum=ExecutionResultService.calc_result_checksum(payload))
        self.begin()
        with patch.object(ExecutionResultService, 'load_result_data', return_value=None):
            self.assertEqual(self.tick(), 0)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (3, 1))
        self.assertTrue(Recovery.read(self.detail.summary_data).result_expected)
        self.now += timedelta(seconds=61)
        with patch.object(ExecutionResultService, 'load_result_data', return_value=payload):
            self.assertEqual(self.tick(), 1)
        self.detail.refresh_from_db(); self.suite.refresh_from_db()
        self.assertEqual((self.detail.status, self.suite.status, self.detail.retry, self.detail.success), (1, 1, 1, 4))
        self.notice.assert_called_once_with(2)

    def test_corrupt_or_cleaned_known_result_is_never_treated_as_no_result(self):
        saved = ExecutionResult.objects.create(source_type='report', target_type='api_case', target_id=11,
            test_suite=self.suite, test_suite_detail=self.detail, status=1,
            result_data=[{'id': 1, 'status': 1}], result_checksum='invalid-checksum')
        self.begin()
        self.assertEqual(self.tick(), 0)
        self.detail.refresh_from_db()
        self.assertTrue(Recovery.read(self.detail.summary_data).result_expected)
        saved.result_cleaned = True
        saved.save(update_fields=['result_cleaned'])
        self.now += timedelta(seconds=61)
        self.assertEqual(self.tick(), 0)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (3, 1))

    def complete_callback(self, *, attempt=1, finalized=True):
        from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult, ApiCaseStepResult, ApiExecutionRequest
        from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
        from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        steps = [ApiCaseStepResult(id=index, parameter_id=index, name='示例场景', status=1,
            api_info_id=1, api_info_name='示例接口', cache_data={},
            request=ApiExecutionRequest(method='GET', url='https://example.com')) for index in range(1, 5)]
        result = ApiCaseExecutionResult(id=11, name='示例用例', project_product_name='示例产品',
            status=1, test_env=0, user_id=1, steps=steps, execution_finalized=finalized)
        payload = [step.model_dump() for step in steps]
        prepared = {'result_data': payload, 'result_object_key': None, 'result_file_name': None,
                    'result_size': 0, 'result_checksum': ExecutionResultService.calc_result_checksum(payload)}
        with patch.object(ExecutionResultService, 'prepare_result_payload', return_value=prepared), \
                patch.object(ExecutionResultService, 'sync_coverage_result'):
            return UpdateTestSuite.update_test_suite_details(TestSuiteDetailResultSchema(
                id=7, type=1, test_suite=2, status=1, attempt=attempt, result_data=result))

    def test_matching_attempt_complete_callback_is_saved_once_then_restored(self):
        self.begin(Cause.EXECUTION_TIMEOUT)
        self.assertTrue(self.complete_callback())
        self.assertTrue(self.complete_callback())
        self.assertEqual(ExecutionResult.objects.count(), 1)
        self.detail.refresh_from_db()
        control = Recovery.read(self.detail.summary_data)
        self.assertEqual((self.detail.status, self.detail.retry, control.result_expected), (3, 1, True))
        self.assertEqual(control.result_id, ExecutionResult.objects.get().id)
        self.notice.assert_not_called()
        self.assertTrue(Recovery.note_owner_ended(7, 1))
        self.assertEqual(self.tick(), 1)
        self.detail.refresh_from_db(); self.suite.refresh_from_db()
        self.assertEqual((self.detail.status, self.suite.status, self.detail.retry, self.detail.success), (1, 1, 1, 4))
        self.notice.assert_called_once_with(2)

    def test_old_incomplete_or_stopped_callbacks_do_not_publish_recovery_results(self):
        self.begin(Cause.EXECUTION_TIMEOUT)
        self.assertFalse(self.complete_callback(attempt=2))
        self.assertFalse(self.complete_callback(finalized=False))
        self.assertEqual(ExecutionResult.objects.count(), 0)
        TestSuite.objects.filter(id=2).update(status=5)
        self.assertFalse(self.complete_callback())
        self.assertEqual(ExecutionResult.objects.count(), 0)

    def test_storage_unknown_result_without_evidence_waits_then_records_exhaustion(self):
        self.begin(Cause.RESULT_UNAVAILABLE)
        self.assertEqual(self.tick(), 0)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (3, 1))
        self.now += timedelta(minutes=6)
        self.assertEqual(self.tick(), 1)
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (0, 1))
        self.event.assert_called_once()

    def test_manual_stop_and_late_result_cannot_revive_new_attempt(self):
        from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
        from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult
        from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
        self.begin(); self.tick()
        TestSuiteDetails.objects.filter(id=7).update(retry=2, status=3)
        result = ApiCaseExecutionResult(id=11, name='示例用例', project_product_name='示例产品',
                                       status=1, test_env=0, user_id=1, steps=[])
        command = TestSuiteDetailResultSchema(id=7, type=1, test_suite=2, status=1, attempt=1, result_data=result)
        with patch('src.apps.test_center.services.reporting.test_suite.update_test_suite.ExecutionResultService.prepare_result_payload', return_value={}):
            self.assertFalse(UpdateTestSuite.update_test_suite_details(command))
        self.detail.refresh_from_db()
        self.assertEqual((self.detail.status, self.detail.retry), (3, 2))
        TestSuite.objects.filter(id=2).update(status=5)
        self.assertEqual(self.tick(), 0)
        self.event.assert_not_called()
