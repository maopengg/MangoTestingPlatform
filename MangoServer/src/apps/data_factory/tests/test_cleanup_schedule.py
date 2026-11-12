from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks


class CleanupScheduleTests(SimpleTestCase):
    def setUp(self):
        self.lease = SimpleNamespace(task_id=3, payload={'execution_id': 7, 'parent_case_detail_id': 17,
                                                       'parent_attempt': 1}, progress={}, generation=0, recovered=False)
        self.execution = SimpleNamespace(cleanup_status=0, cleanup_time=None, save=Mock())
        self.item = SimpleNamespace(id=8, cleanup_status=0)
        patches = [
            patch.object(Tasks, 'claim_cleanup_task', return_value=self.lease),
            patch.object(Tasks, 'finish_cleanup_step', return_value=True),
            patch.object(CleanupPersistenceService, 'lease', side_effect=lambda lease: nullcontext()),
            patch.object(CleanupPersistenceService, 'check'),
            patch.object(DataFactoryCleanup, 'cleanup_execution', return_value={'fail': 0}),
            patch.object(DataFactoryCleanup, 'mark_success'),
            patch.object(DataFactoryCleanup, 'mark_execution_failed'),
            patch.object(DataFactoryCleanup, 'sync_workbench_todo'),
            patch.object(Resources, 'advance', return_value=None),
            patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DatasourceGovernorService.policy',
                  return_value=DatasourcePerformancePolicy()),
            patch.object(Schedule, 'server_now', side_effect=timezone.now),
            patch.object(Resources, 'initialize_observation', return_value=0),
            patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DataFactoryExecution.objects'),
            patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DataFactoryExecutionItem.objects'),
        ]
        self.mocks = []
        for guard in patches:
            self.mocks.append(guard.start())
            self.addCleanup(guard.stop)
        self.mocks[-2].get.return_value = self.execution
        self.mocks[-2].filter.return_value.first.return_value = self.execution
        self.mocks[-1].select_related.return_value.filter.return_value.order_by.return_value = [self.item]
        audit_guard = patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.confirm_resource_requests')
        audit_guard.start()
        self.addCleanup(audit_guard.stop)
        owner_guard = patch.object(Schedule, 'validate_report_owner')
        owner_guard.start()
        self.addCleanup(owner_guard.stop)

    def test_observation_is_rescheduled_without_marking_cleanup_success(self):
        self.mocks[8].return_value = 1800000000
        self.assertTrue(Schedule.run_next())
        self.mocks[5].assert_not_called()
        kwargs = self.mocks[1].call_args.kwargs
        self.assertIn('next_at', kwargs)
        self.assertTrue(self.mocks[1].call_args.args[1]['sql_done'])
        self.assertEqual(self.execution.cleanup_status, 0)

    def test_cleanup_success_clears_old_cleanup_error_but_not_creation_failure(self):
        for execution_status, cleanup_status, expected in ((1, 1, None), (0, 1, 'AUTO_ERROR'),
                                                           (1, 2, 'AUTO_ERROR'), (1, 0, 'AUTO_ERROR')):
            execution = SimpleNamespace(status=execution_status, cleanup_status=cleanup_status,
                                        error_message='AUTO_ERROR')
            DataFactoryCleanup.clear_resolved_cleanup_error(execution)
            self.assertEqual(execution.error_message, expected)

    def test_finalized_cleanup_persists_cleared_error_with_status(self):
        self.execution.status, self.execution.error_message = 1, 'AUTO_OLD_CLEANUP_FAILURE'
        self.mocks[8].return_value = None
        with patch.object(CleanupPersistenceService, 'save') as save:
            Schedule.run_next()
        self.assertEqual(self.execution.cleanup_status, 1)
        self.assertIsNone(self.execution.error_message)
        self.assertIn('error_message', save.call_args.args[1])

    def test_parent_reconciles_exact_request_after_persisted_cleanup_success(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.schemas.cleanup_resource import (
            CleanupResourceState, EsUncertainRequest, EsCleanupCheckResult, EsCleanupSnapshot, EsCleanupRule,
        )
        self.execution.cleanup_status = 1
        self.mocks[-1].filter.return_value.exclude.return_value.exists.return_value = False
        self.mocks[-1].filter.return_value.__iter__.return_value = iter([self.item])
        self.item.cleanup_resources = CleanupResourceState(sql_cleaned=True,
            snapshots=[EsCleanupSnapshot(rule=EsCleanupRule(datasource_alias_id=1, index_template='example'),
                binding_id=2, connection_id=3, connection_version='AUTO_VERSION', environment=0,
                index='example', document_id='1', tenant='7', baseline_absent=True)],
            uncertain_requests=[EsUncertainRequest(request_id='AUTO_DELETE', index='example', document_id='1')],
            results=[EsCleanupCheckResult(index='example', document_id='1', success=True,
                                         checked_at=timezone.now().isoformat(), attempts=10)]).model_dump(mode='json')
        with Infrastructure.scope():
            error = TimeoutError()
            error._datasource_audit_request_id = 'AUTO_DELETE'
            Infrastructure.capture(error, result_unknown=True)
            Schedule.verify_complete(7, require_full_cleanup=True)
            self.assertFalse(Infrastructure.current())

    def test_scheduler_queue_gap_never_consumes_active_cleanup_budget(self):
        self.lease.progress = {'sql_done': True, 'started_at': timezone.now().timestamp() - 3600,
                               'active_seconds': 2.0}
        Schedule.run_next()
        self.mocks[4].assert_not_called()
        self.mocks[5].assert_called_once_with(self.item)
        self.assertTrue(self.mocks[1].call_args.kwargs['success'])
        self.assertLess(self.mocks[1].call_args.args[1]['active_seconds'], 3)

    def test_active_cleanup_budget_accumulates_across_reschedules_but_not_queue_gaps(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        clock = [0.0]
        self.mocks[9].return_value.cleanup_completion_seconds = 1
        self.lease.progress = {'sql_done': True, 'active_seconds': 0.6}
        def sample(*args, **kwargs):
            clock[0] += 0.3
            return 1800000000
        self.mocks[8].side_effect = sample
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.monotonic', side_effect=lambda: clock[0]):
            Schedule.run_next()
            self.assertAlmostEqual(self.lease.progress['active_seconds'], 0.9)
            self.assertIn('next_at', self.mocks[1].call_args.kwargs)
            clock[0] += 10000
            with Infrastructure.scope():
                Schedule.run_next()
                self.assertEqual(Infrastructure.current()[0].code, 34190)
        progress = self.mocks[1].call_args.args[1]
        self.assertAlmostEqual(progress['active_seconds'], 1.2)
        self.assertFalse(progress['verification_failed'])
        self.assertIn('error', self.mocks[1].call_args.kwargs)
        self.mocks[5].assert_not_called()

    def test_true_es_residual_still_fails_verification_without_infrastructure_override(self):
        from src.apps.data_factory.exceptions import DATA_FACTORY_ES_CLEANUP_TIMEOUT
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        self.mocks[8].side_effect = DataFactoryError(DATA_FACTORY_ES_CLEANUP_TIMEOUT)
        with Infrastructure.scope():
            Schedule.run_next()
            self.assertEqual(Infrastructure.current(), [])
        self.assertTrue(self.mocks[1].call_args.args[1]['verification_failed'])
        self.assertIn('error', self.mocks[1].call_args.kwargs)
        self.mocks[5].assert_not_called()

    def test_unexpected_scheduler_fault_preserves_platform_evidence_and_never_passes(self):
        self.mocks[8].side_effect = RuntimeError('AUTO internal fault')
        Schedule.run_next()
        progress = self.mocks[1].call_args.args[1]
        self.assertEqual(progress['infrastructure_issues'][0]['code'], 34193)
        self.assertFalse(progress['verification_failed'])
        self.mocks[5].assert_not_called()
        self.assertIn('error', self.mocks[1].call_args.kwargs)

    def test_sql_admission_wait_is_not_counted_as_cleanup_processing_time(self):
        from src.apps.data_factory.services.governance.datasource_wait import _wait_elapsed
        self.mocks[8].return_value = 1800000000
        initial = timezone.now()
        self.mocks[10].return_value = initial
        self.mocks[10].side_effect = None
        def cleanup(*args, **kwargs):
            _wait_elapsed.set(_wait_elapsed.get() + 600)
            return {'fail': 0}
        token = _wait_elapsed.set(0)
        try:
            self.mocks[4].side_effect = cleanup
            Schedule.run_next()
        finally:
            _wait_elapsed.reset(token)
        progress = self.mocks[1].call_args.args[1]
        self.assertEqual(progress['started_at'], initial.timestamp())
        self.assertLess(progress['active_seconds'], 1)
        self.mocks[5].assert_not_called()
        self.assertNotIn('success', self.mocks[1].call_args.kwargs)

    def test_report_wait_does_not_fail_due_to_queue_delay_or_lose_owner_context(self):
        from src.apps.data_factory.services.cleanup.cleanup_schedule import _case_cleanup_owner, _parent_wait_pulse
        from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
        from src.apps.system.enums.executor import ExecutorTaskStatusEnum
        tasks = Mock()
        tasks.filter.return_value.values.return_value.first.side_effect = [
            {'status': ExecutorTaskStatusEnum.PENDING.value, 'business_id': 7},
            {'status': ExecutorTaskStatusEnum.PENDING.value, 'business_id': 7},
            {'status': ExecutorTaskStatusEnum.SUCCESS.value, 'business_id': 7},
        ]
        pulse = Mock()
        owner = {'parent_case_detail_id': 17, 'parent_attempt': 2}
        details = Mock()
        details.filter.return_value.exists.return_value = True
        def wait(ready, timeout):
            self.assertEqual(timeout, float('inf'))
            # 协作调度器在父 greenlet 查询状态，不得依赖它的 ContextVar。
            token = _case_cleanup_owner.set(None)
            pulse_token = _parent_wait_pulse.set(None)
            try:
                self.assertFalse(ready())
                self.assertTrue(ready())
            finally:
                _case_cleanup_owner.reset(token)
                _parent_wait_pulse.reset(pulse_token)
            return True
        with Schedule.parent_wait(pulse), \
                patch.object(TaskCenterQuerySelector, 'executor_tasks', return_value=tasks), \
                patch('src.apps.test_center.selectors.querysets.TestCenterQuerySelector.test_suite_details',
                      return_value=details), \
                patch('src.apps.task_center.services.execution.cooperative_executor.wait_until', side_effect=wait), \
                patch.object(Schedule, 'verify_complete') as verified:
            token = _case_cleanup_owner.set(owner)
            try:
                Schedule.wait(3)
            finally:
                _case_cleanup_owner.reset(token)
        verified.assert_called_once_with(7, require_full_cleanup=True)
        self.assertEqual(pulse.call_count, 3)
        self.assertEqual(details.filter.call_args.kwargs['retry'], 2)

    def test_unknown_sql_stage_is_not_replayed_after_worker_loss(self):
        self.lease.recovered = True
        self.assertTrue(Schedule.run_next())
        self.mocks[4].assert_not_called()
        self.mocks[6].assert_called_once()
        self.assertIn('error', self.mocks[1].call_args.kwargs)
        self.assertNotIn('ES', self.mocks[1].call_args.kwargs['error'])
        self.mocks[5].assert_not_called()

    def test_verified_sql_stage_is_not_repeated_on_next_sample(self):
        self.lease.progress = {'sql_done': True}
        self.assertTrue(Schedule.run_next())
        self.mocks[4].assert_not_called()
        self.mocks[5].assert_called_once_with(self.item)
        self.assertTrue(self.mocks[1].call_args.kwargs['success'])

    def test_lost_lease_prevents_local_result_write(self):
        lease = object()
        instance = Mock()
        from src.apps.data_factory.services.cleanup.cleanup_persistence import _cleanup_lease
        token = _cleanup_lease.set(lease)
        try:
            with patch.object(Tasks, 'with_cleanup_lease', return_value=(False, None)):
                with self.assertRaises(DataFactoryError):
                    CleanupPersistenceService.save(instance, ['cleanup_status'])
            instance.save.assert_not_called()
        finally:
            _cleanup_lease.reset(token)

    def test_queue_datetime_respects_platform_naive_storage_without_losing_epoch(self):
        from django.test import override_settings
        with override_settings(USE_TZ=False, TIME_ZONE='Asia/Shanghai'):
            value = Schedule.wakeup_at(1800000000)
            self.assertTrue(timezone.is_naive(value))
            self.assertEqual(timezone.make_aware(value, timezone.get_default_timezone()).timestamp(), 1800000000)

    def test_invalid_progress_fails_before_sql_or_resource_execution(self):
        self.lease.progress = {'invalid_snapshot': True}
        self.assertTrue(Schedule.run_next())
        self.mocks[4].assert_not_called()
        self.mocks[8].assert_not_called()
        self.assertIn('快照格式不正确', self.mocks[1].call_args.kwargs['error'])

    def test_inline_resource_read_error_preserves_failure_not_success(self):
        self.lease.payload['mode'] = 'synchronous'
        self.mocks[8].side_effect = TimeoutError('example read timeout')
        Schedule.run_claimed(self.lease, inline=True)
        self.mocks[5].assert_not_called()
        self.mocks[6].assert_called_once()
        self.assertIn('error', self.mocks[1].call_args.kwargs)
        self.assertFalse(self.mocks[1].call_args.kwargs.get('success', False))

    def test_scheduler_infrastructure_failure_survives_persisted_progress(self):
        from src.apps.data_factory.exceptions import DATASOURCE_GOVERNOR_UNAVAILABLE
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        def cleanup(*args, **kwargs):
            Infrastructure.capture(DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE))
            return {'fail': 1}
        self.mocks[4].side_effect = cleanup
        Schedule.run_next()
        progress = self.mocks[1].call_args.args[1]
        with Infrastructure.scope():
            Schedule.restore_infrastructure(progress)
            self.assertEqual([issue.code for issue in Infrastructure.current()],
                             [DATASOURCE_GOVERNOR_UNAVAILABLE.code])
        self.assertIn('error', self.mocks[1].call_args.kwargs)
        self.mocks[5].assert_not_called()

    def test_business_cleanup_failure_has_no_infrastructure_override(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        self.mocks[4].return_value = {'fail': 1}
        Schedule.run_next()
        with Infrastructure.scope():
            Schedule.restore_infrastructure(self.mocks[1].call_args.args[1])
            self.assertEqual(Infrastructure.current(), [])
        self.assertIn('error', self.mocks[1].call_args.kwargs)

    def test_parent_wait_restores_scheduler_failure_origin(self):
        from src.apps.data_factory.exceptions import DATASOURCE_GOVERNOR_UNAVAILABLE
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
        from src.apps.system.enums.executor import ExecutorTaskStatusEnum
        tasks = Mock()
        tasks.filter.return_value.values.return_value.first.return_value = {
            'status': ExecutorTaskStatusEnum.FAILED.value, 'business_id': 7,
            'error_message': 'SQL 清理未完成', 'progress_data': {'infrastructure_issues': [{
                'code': DATASOURCE_GOVERNOR_UNAVAILABLE.code,
                'message': DATASOURCE_GOVERNOR_UNAVAILABLE.message, 'origin': 'platform'}]}}
        def wait(ready, timeout):
            self.assertTrue(ready())
        with Infrastructure.scope(), \
                patch.object(TaskCenterQuerySelector, 'executor_tasks', return_value=tasks), \
                patch('src.apps.task_center.services.execution.cooperative_executor.wait_until', side_effect=wait):
            with self.assertRaises(DataFactoryError):
                Schedule.wait(3)
            self.assertEqual(Infrastructure.current()[0].code, DATASOURCE_GOVERNOR_UNAVAILABLE.code)

    def test_missing_task_and_control_database_disconnect_are_platform_not_business_errors(self):
        from django.db import OperationalError
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
        for failure in (None, OperationalError('AUTO control connection lost')):
            tasks = Mock()
            tasks.filter.return_value.values.return_value.first.return_value = None
            tasks.filter.return_value.values.return_value.first.side_effect = failure
            with self.subTest(failure=type(failure).__name__), Infrastructure.scope(), \
                    patch.object(TaskCenterQuerySelector, 'executor_tasks', return_value=tasks), \
                    patch('src.apps.task_center.services.execution.cooperative_executor.wait_until',
                          side_effect=lambda ready, timeout: ready()):
                with self.assertRaises(DataFactoryError) as caught:
                    Schedule.wait(3)
                self.assertEqual(caught.exception.code, 34193)
                self.assertEqual(Infrastructure.current()[0].code, 34193)

    def test_legacy_ambiguous_failure_requires_review_but_known_verification_failure_is_preserved(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.system.enums.executor import ExecutorTaskStatusEnum
        with Infrastructure.scope():
            with self.assertRaises(DataFactoryError) as caught:
                Schedule.require_failure_evidence({'status': ExecutorTaskStatusEnum.FAILED.value,
                                                  'progress_data': {}})
            self.assertEqual(caught.exception.code, 34193)
        with Infrastructure.scope():
            Schedule.require_failure_evidence({'status': ExecutorTaskStatusEnum.FAILED.value,
                                              'progress_data': {'verification_failed': True}})
            self.assertEqual(Infrastructure.current(), [])

    def test_nested_inline_cleanup_keeps_unknown_result_in_parent_scope(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        self.lease.payload['mode'] = 'synchronous'
        self.mocks[8].side_effect = TimeoutError('example read timeout')
        with Infrastructure.scope():
            Schedule.run_claimed(self.lease, inline=True)
            self.assertTrue(Infrastructure.current())
        self.assertIn('error', self.mocks[1].call_args.kwargs)


class CleanupTaskClaimTests(SimpleTestCase):
    @patch('src.apps.task_center.services.execution.executor_task.transaction.atomic', side_effect=lambda: nullcontext())
    @patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects')
    def test_corrupt_generation_reaches_explicit_snapshot_failure_instead_of_poison_queue(self, objects, atomic):
        from src.apps.system.enums.executor import ExecutorTaskStatusEnum
        for progress in ([{}], {'generation': 'invalid'}, {'generation': -1}):
            task = SimpleNamespace(id=3, status=ExecutorTaskStatusEnum.PENDING.value,
                                   progress_data=progress, payload={'execution_id': 7}, started_at=None, save=Mock())
            objects.select_for_update.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = task
            lease = Tasks.claim_cleanup_task()
            self.assertEqual(lease.progress, {'invalid_snapshot': True})
            self.assertEqual(lease.generation, 0)
            task.save.assert_called_once()
