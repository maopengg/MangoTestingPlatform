from contextlib import nullcontext
from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum, DataFactoryCleanupStatusEnum
from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_CONFIG_INVALID
from src.apps.data_factory.schemas.cleanup_resource import CleanupTaskPayload, CleanupResourceState
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.execution_recovery import DataFactoryExecutionRecovery
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.task_center.schemas.server_task import ServerTaskLease
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks
from src.apps.system.enums.executor import ExecutorTaskStatusEnum


class CleanupRoutingTests(SimpleTestCase):
    def setUp(self):
        from src.apps.data_factory.services.cleanup_schedule import _case_cleanup_owner
        token = _case_cleanup_owner.set(None)
        self.addCleanup(_case_cleanup_owner.reset, token)
        self.execution = SimpleNamespace(id=7, project_product_id=4)
        self.task = SimpleNamespace(id=3)
        self.lease = ServerTaskLease(task_id=3, token='example', generation=0, recovered=False,
                                    payload={'execution_id': 7, 'mode': 'synchronous'})
        patches = {
            'inline': patch.object(Tasks, 'begin_inline_cleanup', return_value=(self.task, self.lease)),
            'run': patch.object(Schedule, 'run_inline'),
            'enqueue': patch.object(Schedule, 'enqueue', return_value=self.task),
            'wait': patch.object(Schedule, 'wait'),
            'validate': patch.object(Schedule, 'validate_report_owner'),
            'verify': patch.object(Schedule, 'verify_complete'),
            'query': patch('src.apps.data_factory.services.cleanup_schedule.TaskCenterQuerySelector.executor_tasks'),
        }
        self.mocks = {}
        for key, guard in patches.items():
            self.mocks[key] = guard.start()
            self.addCleanup(guard.stop)
        self.status = self.mocks['query'].return_value.filter.return_value.values.return_value.first
        self.status.return_value = {'status': ExecutorTaskStatusEnum.SUCCESS.value, 'error_message': None}

    def test_active_cleanup_renews_near_expiry_without_reviving_old_ownership(self):
        now = datetime(2026, 11, 4, tzinfo=dt_timezone.utc)
        for remaining, token, accepted in ((10, 'example', True), (50, 'example', True),
                                           (-1, 'example', False), (10, 'replaced', False)):
            with self.subTest(remaining=remaining, token=token):
                task = SimpleNamespace(status=ExecutorTaskStatusEnum.RUNNING.value,
                                       progress_data={'claim_token': token},
                                       lease_expires_at=now + timedelta(seconds=remaining), save=Mock())
                callback = Mock(return_value='checked')
                with patch('src.apps.task_center.services.execution.executor_task.transaction.atomic',
                           side_effect=lambda: nullcontext()), \
                        patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as tasks, \
                        patch('src.apps.task_center.services.execution.executor_task.timezone.now', return_value=now):
                    tasks.select_for_update.return_value.get.return_value = task
                    result = Tasks.with_cleanup_lease(self.lease, callback)
                self.assertEqual(result[0], accepted)
                self.assertEqual(callback.call_count, int(accepted))
                renewed = accepted and remaining <= 30
                self.assertEqual(task.save.call_count, int(renewed))
                if renewed:
                    self.assertEqual(task.lease_expires_at, now + timedelta(seconds=60))

    def test_no_report_cleans_inline_without_queue_or_scheduler_wait(self):
        self.assertEqual(Schedule.execute(self.execution), 3)
        self.mocks['run'].assert_called_once_with(self.lease)
        self.mocks['enqueue'].assert_not_called()
        self.mocks['wait'].assert_not_called()
        self.mocks['verify'].assert_called_once_with(7, require_full_cleanup=True)

    def test_existing_inline_cleanup_is_waited_without_duplicate_delete(self):
        self.mocks['inline'].return_value = (self.task, None)
        self.assertEqual(Schedule.execute(self.execution), 3)
        self.mocks['wait'].assert_called_once_with(3, require_full_cleanup=True)
        self.mocks['run'].assert_not_called()
        self.mocks['enqueue'].assert_not_called()

    def test_formal_report_uses_validated_report_owner_and_persistent_queue(self):
        token = Schedule.set_owner(17, 1)
        try:
            self.assertEqual(Schedule.execute(self.execution), 3)
        finally:
            Schedule.reset_owner(token)
        self.mocks['validate'].assert_called_once_with(
            {'parent_case_detail_id': 17, 'parent_attempt': 1}, self.execution)
        self.mocks['enqueue'].assert_called_once()
        self.mocks['wait'].assert_called_once_with(3, require_full_cleanup=True)
        self.mocks['inline'].assert_not_called()

    def test_invalid_formal_report_does_not_fall_back_to_inline(self):
        self.mocks['validate'].side_effect = DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('example',))
        token = Schedule.set_owner(17, 1)
        try:
            with self.assertRaises(DataFactoryError):
                Schedule.execute(self.execution)
        finally:
            Schedule.reset_owner(token)
        self.mocks['inline'].assert_not_called()
        self.mocks['enqueue'].assert_not_called()

    def test_context_provided_by_user_cannot_forge_report_routing(self):
        self.assertEqual(Schedule.execution_context({CLEANUP_REPORT_CONTEXT_KEY: {
            'parent_case_detail_id': 99, 'parent_attempt': 99}}), {})
        token = Schedule.set_owner(17, 1)
        try:
            saved = Schedule.execution_context({CLEANUP_REPORT_CONTEXT_KEY: {'forged': True}})
            self.assertEqual(saved[CLEANUP_REPORT_CONTEXT_KEY], {'parent_case_detail_id': 17, 'parent_attempt': 1})
            with Schedule.report_scope():
                self.assertIsNone(Schedule.current_owner())
            self.assertEqual(Schedule.current_owner(), saved[CLEANUP_REPORT_CONTEXT_KEY])
        finally:
            Schedule.reset_owner(token)

    def test_failed_inline_task_is_not_reported_as_success(self):
        self.mocks['inline'].return_value = (self.task, None)
        self.status.return_value = {'status': ExecutorTaskStatusEnum.FAILED.value, 'error_message': 'example failure'}
        self.mocks['wait'].side_effect = DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('example failure',))
        with self.assertRaises(DataFactoryError):
            Schedule.execute(self.execution)
        self.mocks['run'].assert_not_called()
        self.mocks['wait'].assert_called_once_with(3, require_full_cleanup=True)

    def test_payload_defaults_preserve_old_scheduled_tasks(self):
        self.assertEqual(CleanupTaskPayload.model_validate({'execution_id': 7}, strict=True).mode,
                         DataFactoryCleanupModeEnum.SCHEDULED)
        self.assertEqual(CleanupTaskPayload.model_validate(self.lease.payload, strict=True).mode,
                         DataFactoryCleanupModeEnum.SYNCHRONOUS)

class CleanupCompletionProofTests(SimpleTestCase):
    @patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecution.objects')
    @patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecutionItem.objects')
    def test_root_success_cannot_hide_uncleaned_child(self, items, executions):
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
        executions.get.return_value = SimpleNamespace(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value)
        items.filter.return_value.exclude.return_value.exists.return_value = True
        with Infrastructure.scope():
            with self.assertRaises(DataFactoryError) as caught:
                Schedule.verify_complete(7, require_full_cleanup=True)
            self.assertEqual(caught.exception.code, 34193)
            self.assertTrue(Infrastructure.current())

    @patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecution.objects')
    @patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecutionItem.objects')
    def test_task_success_cannot_replace_actual_cleanup_proof(self, items, executions):
        for state in (DataFactoryCleanupStatusEnum.FAIL.value, DataFactoryCleanupStatusEnum.NOT_CLEANED.value):
            executions.get.return_value = SimpleNamespace(cleanup_status=state)
            for required in (True, False):
                with self.assertRaises(DataFactoryError):
                    Schedule.verify_complete(7, require_full_cleanup=required)
        executions.get.return_value = SimpleNamespace(cleanup_status=DataFactoryCleanupStatusEnum.SKIPPED.value)
        items.filter.return_value.exists.return_value = True
        with self.assertRaises(DataFactoryError):
            Schedule.verify_complete(7, require_full_cleanup=True)
        Schedule.verify_complete(7, require_full_cleanup=False)
        items.filter.return_value.exists.return_value = False
        items.filter.return_value.exclude.return_value.exists.return_value = False
        Schedule.verify_complete(7, require_full_cleanup=True)


class InlineCleanupOwnershipTests(SimpleTestCase):
    @patch('src.apps.task_center.services.execution.executor_task.transaction.atomic', side_effect=lambda: nullcontext())
    @patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects')
    def test_scheduler_claim_explicitly_excludes_inline_tasks(self, objects, atomic):
        objects.select_for_update.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None
        self.assertIsNone(Tasks.claim_cleanup_task())
        condition = str(objects.select_for_update.return_value.filter.return_value.filter.call_args.args[0])
        self.assertIn("('payload__mode__isnull', True)", condition)
        self.assertIn("NOT (AND: ('payload__mode', 'synchronous'))", condition)

    @patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects')
    @patch.object(Tasks, 'create_cleanup_task')
    def test_inline_ownership_is_acquired_before_external_work(self, create, objects):
        task = SimpleNamespace(id=3, status=ExecutorTaskStatusEnum.PENDING.value,
                               payload={'execution_id': 7, 'mode': 'synchronous'}, save=Mock())
        create.return_value = task
        objects.select_for_update.return_value.get.return_value = task
        result, lease = Tasks.begin_inline_cleanup.__wrapped__(Tasks, 7)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.RUNNING.value)
        self.assertEqual(task.progress_data['claim_token'], lease.token)
        self.assertIs(result, task)
        task.save.assert_called_once()
        task.status = ExecutorTaskStatusEnum.RUNNING.value
        repeated, duplicate_lease = Tasks.begin_inline_cleanup.__wrapped__(Tasks, 7)
        self.assertIs(repeated, task)
        self.assertIsNone(duplicate_lease)
        task.save.assert_called_once()

    @patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects')
    def test_lost_inline_owner_is_failed_without_replaying_delete(self, objects):
        task = SimpleNamespace(id=12, business_id=7, lease_expires_at=datetime.now(dt_timezone.utc),
                               progress_data={'sql_done': False}, save=Mock())
        objects.select_for_update.return_value.filter.return_value.order_by.return_value.__getitem__.return_value = [task]
        self.assertEqual(Tasks.expire_inline_cleanup_tasks.__wrapped__(Tasks), [7])
        self.assertEqual(task.status, ExecutorTaskStatusEnum.FAILED.value)
        self.assertFalse(task.progress_data['sql_done'])
        self.assertEqual(task.progress_data['infrastructure_issues'][0]['code'], 34189)
        self.assertIsNone(task.lease_expires_at)
        self.assertIn('不会自动重放', task.error_message)


class InlineResourceWindowTests(SimpleTestCase):
    def test_quota_wait_inside_first_sample_cannot_replace_full_observation_window(self):
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupRule, EsCleanupSnapshot
        from src.apps.data_factory.services.datasource_wait import _wait_elapsed
        rule = EsCleanupRule(datasource_alias_id=8, index_template='example_{tenant}', timeout_seconds=3)
        snapshot = EsCleanupSnapshot(rule=rule, binding_id=5, connection_id=6, connection_version='example',
            environment=0, index='example_1', document_id='11', tenant='1', baseline_absent=True)
        item = SimpleNamespace(execution=SimpleNamespace(project_product_id=1), save=Mock(),
            cleanup_resources=CleanupResourceState(snapshots=[snapshot], sql_cleaned=True).model_dump(mode='json'))
        now = [1000.0]
        samples = []
        def sample(*args, **kwargs):
            if not samples:
                now[0] += 600
                _wait_elapsed.set(_wait_elapsed.get() + 600)
            samples.append(now[0])
            return True
        clock = lambda: datetime.fromtimestamp(now[0], dt_timezone.utc)
        token = _wait_elapsed.set(0)
        try:
            with patch.object(Resources, 'validate_snapshot', side_effect=lambda value: Resources.state(value)), \
                    patch.object(Resources, 'resolve_binding'), \
                    patch('src.apps.data_factory.services.cleanup_resource.DatasourceTargetService.resolve'), \
                    patch('src.apps.data_factory.services.factory_sql_execution.DataFactorySqlExecutionService.build_source_context',
                          return_value={}), patch.object(Resources, 'sample', side_effect=sample):
                due = Resources.advance(item, generation=0, task_id=3, clock=clock)
                state = Resources.state(item)
                self.assertEqual(state.checkpoints[0].deadline, 1603)
                self.assertFalse(state.results)
                while due is not None:
                    now[0] = due
                    due = Resources.advance(item, generation=0, task_id=3, clock=clock)
                self.assertGreaterEqual(samples[-1] - samples[0], 3)
                self.assertEqual(Resources.state(item).checkpoints[0].final_count, 2)
        finally:
            _wait_elapsed.reset(token)

    @patch.object(Resources, 'validate_snapshot')
    @patch.object(Resources, 'resolve_binding')
    @patch('src.apps.data_factory.services.cleanup_resource.DatasourceTargetService.resolve')
    @patch.object(Resources, 'sample', return_value=True)
    def test_inline_uses_same_full_window_and_two_terminal_samples(self, sample, target, binding, validate):
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupRule, EsCleanupSnapshot
        rule = EsCleanupRule(datasource_alias_id=8, index_template='example_{tenant}', timeout_seconds=3)
        snapshot = EsCleanupSnapshot(rule=rule, binding_id=9, connection_id=10, connection_version='example',
            environment=0, index='example_7', document_id='1001', tenant='7', baseline_absent=True)
        execution = SimpleNamespace(id=7, execution_no='DFEXAMPLE', project_product_id=4,
            source_id=8, source_type=4, stage=2, cleanup_status=0, save=Mock())
        item = SimpleNamespace(id=11, execution=execution, cleanup_status=0, cleanup_strategy=1,
            cleanup_resources=CleanupResourceState(snapshots=[snapshot], sql_cleaned=True).model_dump(mode='json'), save=Mock())
        validate.side_effect = lambda value: Resources.state(value)
        now = [1800000000.0]
        samples = []
        sample.side_effect = lambda *args, **kwargs: samples.append(now[0]) or True
        lease = ServerTaskLease(task_id=3, token='example', generation=0, recovered=False,
                               payload={'execution_id': 7, 'mode': 'synchronous'})
        from src.apps.data_factory.services.cleanup_persistence import CleanupPersistenceService
        with patch.object(Schedule, 'server_now', side_effect=lambda: datetime.fromtimestamp(now[0], dt_timezone.utc)), \
                patch('src.apps.data_factory.services.cleanup_schedule.sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)), \
                patch('src.apps.data_factory.services.cleanup_schedule.DatasourceGovernorService.policy', return_value=DatasourcePerformancePolicy()), \
                patch.object(CleanupPersistenceService, 'lease', side_effect=lambda value: nullcontext()), \
                patch.object(CleanupPersistenceService, 'check'), \
                patch.object(DataFactoryCleanup, 'cleanup_execution', return_value={'fail': 0}) as sql, \
                patch.object(DataFactoryCleanup, 'mark_success', side_effect=lambda value: setattr(value, 'cleanup_status', 1)), \
                patch.object(DataFactoryCleanup, 'mark_execution_failed') as failure, \
                patch.object(DataFactoryCleanup, 'sync_workbench_todo'), \
                patch.object(Tasks, 'finish_cleanup_step', return_value=True) as finish, \
                patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecution.objects') as executions, \
                patch('src.apps.data_factory.services.cleanup_schedule.DataFactoryExecutionItem.objects') as items:
            executions.get.return_value = execution
            items.select_related.return_value.filter.return_value.order_by.return_value = [item]
            Schedule.run_inline(lease)
        sql.assert_called_once_with(7, force_cleanup=True, allow_missing=True, defer_resources=True)
        self.assertEqual(samples, [1800000000, 1800000002, 1800000003, 1800000004])
        self.assertEqual(execution.cleanup_status, DataFactoryCleanupStatusEnum.SUCCESS.value)
        self.assertEqual(item.cleanup_resources['results'][0]['snapshot_index'], 0)
        self.assertTrue(finish.call_args.kwargs['success'])
        failure.assert_not_called()


class InterruptedExecutionRoutingTests(SimpleTestCase):
    @patch.object(DataFactoryExecutionRecovery, 'recover_inline_cleanup', return_value=0)
    @patch.object(DataFactoryExecutionRecovery, 'reconcile_manual_cleanup_states', return_value={'pending': 0, 'resolved': 0})
    @patch('src.apps.data_factory.services.execution_recovery.DataFactoryExecution.objects')
    @patch.object(DataFactoryCleanup, 'mark_execution_failed')
    @patch.object(Schedule, 'enqueue')
    def test_no_report_orphan_creates_failure_responsibility_not_scheduler_work(self, enqueue, failure, executions, manual, expired):
        execution = SimpleNamespace(id=7, status=1, context={}, project_product_id=4)
        executions.filter.return_value.filter.return_value.distinct.return_value.order_by.return_value.__getitem__.return_value = [execution]
        result = DataFactoryExecutionRecovery.recover()
        self.assertEqual(result['data_factory_recovery_failed_count'], 1)
        failure.assert_called_once()
        enqueue.assert_not_called()
