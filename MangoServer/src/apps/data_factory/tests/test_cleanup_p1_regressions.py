from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import datetime, timezone as datetime_timezone
from threading import Barrier, Lock
from time import monotonic, sleep
from types import SimpleNamespace as N
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.constants import EXECUTION_OWNER_CONTEXT_KEY
from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_CLEANUP_COORDINATION_FAILED
from src.apps.data_factory.schemas.cleanup_resource import FactoryExecutionOwner
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService as Persistence
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup as Cleanup
from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService as Wait
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.execution.parts.execution import DataFactoryRunnerExecutionMixin
from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation as Reconcile
from src.apps.data_factory.services.recovery.execution_recovery import DataFactoryExecutionRecovery as Recovery
from src.apps.data_factory.tests import test_cleanup_schedule as schedule_fixtures
from src.apps.data_factory.tests import test_factory_reliability_regressions as resource_fixtures
from src.apps.task_center.models import WorkbenchTodo
from src.apps.task_center.services.workbench.todo import WorkbenchTodoService as Todos
from src.apps.data_factory.models import DataFactoryExecution


class ObservationBatchTests(SimpleTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.lease = N(task_id=3, generation=0, token='AUTO_TOKEN')
        self.stack.enter_context(patch.object(Schedule, 'server_now', return_value=timezone.now()))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DatasourceGovernorService.policy',
            return_value=DatasourcePerformancePolicy(pool_size=4)))
        self.success = self.stack.enter_context(patch.object(Cleanup, 'mark_success'))
        self.stack.enter_context(patch.object(Resources, 'resolve_verified'))

    def test_single_claim_only_activates_and_advances_32_of_101_items(self):
        fixture = schedule_fixtures.CleanupScheduleTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        items = [N(id=i + 100, cleanup_status=0, cleanup_strategy=1, cleanup_resources={}) for i in range(101)]
        fixture.mocks[-1].select_related.return_value.filter.return_value.order_by.return_value = items
        fixture.mocks[8].return_value = 2000000000
        Schedule.run_claimed_step(fixture.lease)
        self.assertEqual(fixture.mocks[11].call_count, 32)
        self.assertEqual(fixture.mocks[8].call_count, 32)
        self.assertEqual(fixture.mocks[-1].select_related.call_count, 1)
        self.assertEqual(fixture.mocks[1].call_count, 1)

    def test_probes_are_bounded_and_do_not_inherit_case_greenlets_or_leases(self):
        from greenlet import getcurrent
        from src.apps.data_factory.services.cleanup import cleanup_persistence
        barrier, lock, identities = Barrier(4), Lock(), []
        def sample(item, **kwargs):
            self.assertIsNone(getcurrent().parent)
            self.assertIs(cleanup_persistence._cleanup_lease.get(), self.lease)
            barrier.wait(timeout=3)
            with lock:
                identities.append(item.id)
            return 2000000000
        with patch.object(Resources, 'advance', side_effect=sample), Infrastructure.scope():
            pending, _ = Schedule.probe_observations([(N(id=i, cleanup_resources={}), 0) for i in range(4)], self.lease)
        self.assertEqual(len(pending), 4)
        self.assertCountEqual(identities, range(4))
        self.assertIsNone(cleanup_persistence._cleanup_lease.get())

    def test_failure_waits_for_other_sent_probes_and_cannot_report_success(self):
        barrier, finished = Barrier(2), []
        error = DataFactoryError(DATA_FACTORY_CLEANUP_COORDINATION_FAILED, value=('AUTO owner changed',))
        def sample(item, **kwargs):
            barrier.wait(timeout=3)
            if item.id == 1:
                raise error
            sleep(0.02)
            finished.append(item.id)
            return 2000000000
        with patch.object(Resources, 'advance', side_effect=sample), Infrastructure.scope():
            with self.assertRaises(DataFactoryError):
                Schedule.probe_observations([(N(id=1, cleanup_resources={}), 0), (N(id=2, cleanup_resources={}), 0)], self.lease)
            self.assertTrue(Infrastructure.current())
        self.assertEqual(finished, [2])
        self.success.assert_not_called()

    def test_future_probes_are_not_run_early(self):
        with patch.object(Resources, 'advance') as advance:
            pending, waited = Schedule.probe_observations([(N(id=1), 2000000000)], self.lease)
        self.assertEqual(len(pending), 1)
        self.assertEqual(waited, 0)
        advance.assert_not_called()

    def test_single_connection_still_batches_without_reloading_all_items(self):
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DatasourceGovernorService.policy',
                   return_value=DatasourcePerformancePolicy(pool_size=1)), \
                patch.object(Resources, 'advance', return_value=2000000000) as advance:
            pending, _ = Schedule.probe_observations([(N(id=i), 0) for i in range(40)], self.lease)
        self.assertEqual(advance.call_count, 32)
        self.assertEqual(len(pending), 40)

    def test_retained_manual_resource_does_not_waive_auto_resource_proof(self):
        fixture = schedule_fixtures.CleanupScheduleTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.item.cleanup_strategy = 1
        fixture.item.cleanup_resources = {}
        fixture.mocks[-1].select_for_update.return_value.filter.return_value = [
            fixture.item, N(id=9, cleanup_status=4, cleanup_strategy=2, cleanup_resources={})]
        with self.assertRaises(DataFactoryError), patch.object(Persistence, 'save') as save:
            Schedule.persist_verified_execution(7, fixture.lease, {}, skipped=True)
        save.assert_not_called()

    def test_parallel_wait_is_wall_time_not_sum_of_worker_waits(self):
        barrier = Barrier(4)
        def sample(item, **kwargs):
            barrier.wait(timeout=3)
            start = monotonic()
            sleep(0.02)
            Wait.record_interval(start, monotonic())
            return 2000000000
        with patch.object(Resources, 'advance', side_effect=sample):
            _, waited = Schedule.probe_observations([(N(id=i, cleanup_resources={}), 0) for i in range(4)], self.lease)
        self.assertGreater(waited, 0.01)
        self.assertLess(waited, 0.06)

    def test_101_resources_finish_full_30_second_windows_without_checkpoint_restarts(self):
        fixture = resource_fixtures.LateEsRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.snapshot.rule.timeout_seconds = 30
        fixture.state.snapshots = [fixture.snapshot]
        fixture.item.cleanup_resources = fixture.state.model_dump(mode='json')
        items = [deepcopy(fixture.item) for _ in range(101)]
        for i, item in enumerate(items):
            item.id = 100 + i
            item.cleanup_resources['snapshots'][0]['document_id'] = str(item.id)
        pending = [(item, 1800000000) for item in items]
        at = [1800000000]
        with patch.object(Schedule, 'server_now', side_effect=lambda: datetime.fromtimestamp(at[0], datetime_timezone.utc)), \
                patch('src.apps.data_factory.services.cleanup.cleanup_resource.logger.debug'):
            for second in (*range(0, 30, 4), 30, 32):
                at[0] = 1800000000 + second
                while any(due <= at[0] for _, due in pending):
                    pending, _ = Schedule.probe_observations(pending, self.lease)
        self.assertFalse(pending)
        self.assertEqual(self.success.call_count, 101)
        for item in items:
            check = item.cleanup_resources['checkpoints'][0]
            self.assertEqual(check['restart_count'], 0)
            self.assertGreaterEqual(check['last_checked_at'] - check['started_at'], 30)
            self.assertGreaterEqual(check['final_count'], 2)
            self.assertEqual(len(item.cleanup_resources['results']), 1)


class CleanupTodoRaceTests(SimpleTestCase):
    def test_stale_failure_snapshot_cannot_reopen_todo_after_cleanup_succeeded(self):
        now = timezone.now()
        execution = N(id=11, cleanup_status=1, cleanup_time=now, update_time=now)
        with patch.object(DataFactoryExecution.objects, 'select_for_update') as executions, \
                patch.object(Todos, '_upsert') as create:
            executions.return_value.filter.return_value.first.return_value = execution
            result = Todos._upsert_cleanup_failure.__wrapped__(Todos, 'AUTO_OLD_FAILURE', {'source_id': 11})
        self.assertIsNone(result)
        create.assert_not_called()

    def test_new_failure_inserted_during_scan_is_not_in_close_candidates(self):
        existing = Mock()
        existing.values_list.return_value = [(1, 11)]
        executions = Mock()
        executions.filter.return_value.prefetch_related.return_value = [N(id=11)]
        new_todo = N(id=2, event_key='AUTO_NEW_FAILURE')
        with patch.object(WorkbenchTodo.objects, 'filter', return_value=existing), \
                patch.object(DataFactoryExecution.objects, 'select_related', return_value=executions), \
                patch.object(Todos, 'record_data_factory_cleanup_failure', return_value=new_todo), \
                patch.object(Todos, 'reconcile_cleanup_todo', return_value=0) as close, \
                patch.object(Todos, '_notify_cleanup_failure_if_due'):
            Todos.reconcile_data_factory_cleanup_todos()
        close.assert_called_once_with(1, 11)

    def test_fresh_execution_failure_is_preserved_even_if_missing_from_scan(self):
        now = timezone.now()
        execution = N(id=11, cleanup_status=2, cleanup_time=now, update_time=now)
        todo = N(id=1, event_type=6,
            event_key=f'data-factory:execution:11:cleanup-failed:{Todos._timestamp_key(now)}')
        with patch.object(DataFactoryExecution.objects, 'select_for_update') as executions, \
                patch.object(WorkbenchTodo.objects, 'select_for_update') as todos, \
                patch.object(Todos, '_cleanup_items', return_value=[N(cleanup_status=2)]), \
                patch.object(Todos, '_resolve_queryset') as resolve:
            executions.return_value.filter.return_value.first.return_value = execution
            todos.return_value.filter.return_value.first.return_value = todo
            result = Todos.reconcile_cleanup_todo.__wrapped__(Todos, 1, 11)
        self.assertEqual(result, 0)
        resolve.assert_not_called()

    def test_all_140_items_verified_can_close_without_changing_case_result(self):
        now = timezone.now()
        execution = N(id=11, cleanup_status=2, cleanup_time=now, update_time=now)
        todo = N(id=1, event_type=6,
            event_key=f'data-factory:execution:11:cleanup-failed:{Todos._timestamp_key(now)}')
        items = [N(cleanup_status=1, cleanup_resources={'sql_cleaned': True}) for _ in range(140)]
        with patch.object(DataFactoryExecution.objects, 'select_for_update') as executions, \
                patch.object(WorkbenchTodo.objects, 'select_for_update') as todos, \
                patch.object(WorkbenchTodo.objects, 'filter'), \
                patch.object(Todos, '_cleanup_items', return_value=items), \
                patch.object(Todos, '_resolve_queryset', return_value=1) as resolve:
            executions.return_value.filter.return_value.first.return_value = execution
            todos.return_value.filter.return_value.first.return_value = todo
            self.assertEqual(Todos.reconcile_cleanup_todo.__wrapped__(Todos, 1, 11), 1)
        resolve.assert_called_once()
        self.assertEqual(execution.cleanup_status, 2)

    def test_success_flag_without_resource_proof_does_not_close_failure(self):
        now = timezone.now()
        execution = N(id=11, cleanup_status=1, cleanup_time=now, update_time=now)
        todo = N(id=1, event_type=6, event_key='AUTO_OLD_FAILURE')
        with patch.object(DataFactoryExecution.objects, 'select_for_update') as executions, \
                patch.object(WorkbenchTodo.objects, 'select_for_update') as todos, \
                patch.object(Todos, '_cleanup_items', return_value=[N(cleanup_status=1, cleanup_resources={})]), \
                patch.object(Todos, '_resolve_queryset') as resolve:
            executions.return_value.filter.return_value.first.return_value = execution
            todos.return_value.filter.return_value.first.return_value = todo
            self.assertEqual(Todos.reconcile_cleanup_todo.__wrapped__(Todos, 1, 11), 0)
        resolve.assert_not_called()


class DebugCleanupHandoffTests(SimpleTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.execution = N(id=7, execution_no='DF_AUTO', context={}, save=Mock(), refresh_from_db=Mock())
        class Runner(DataFactoryRunnerExecutionMixin):
            get_template = Mock(return_value=N(id=1, project_product_id=1, project_product=1, module=1))
            require_template_entities_available = Mock()
            split_scene_overrides = Mock(return_value=({}, {}))
            build_execution_no = Mock(return_value='DF_AUTO')
            create_by_template = Mock(return_value={'id': 1})
            create_template_items = Mock(return_value=[])
            execute_post_insert_updates = Mock(return_value=[])
            build_output = Mock(return_value={})
            resolve_execution_cleanup_status = Mock(return_value=0)
            sync_execution_cleanup_todo = Mock()
            cleanup_failed_execution = Mock()
        self.runner = Runner
        Runner.get_template.return_value.output_config = {}
        self.stack.enter_context(patch('src.apps.data_factory.services.execution.parts.execution.DataFactoryExecution.objects.create',
                                     return_value=self.execution))
        self.stack.enter_context(patch('src.apps.data_factory.services.execution.parts.execution.DataFactoryRuntimeCache.bind_context',
                                     side_effect=lambda *args: nullcontext()))
        self.stack.enter_context(patch.object(Schedule, 'execution_context', return_value={}))
        self.cleanup = self.stack.enter_context(patch.object(Schedule, 'execute'))
        self.failed_wait = self.stack.enter_context(patch.object(Schedule, 'record_wait_failure'))
        self.owner = FactoryExecutionOwner(process_token='AUTO_PROCESS', process_started_at='AUTO_START', worker_name='AUTO_WORKER')

    def run_debug(self):
        return self.runner.debug_run_template(1, test_object_id=1, test_env=0, test_data=N())

    def test_successful_auto_debug_is_cleaned_before_return(self):
        self.cleanup.side_effect = lambda *args, **kw: setattr(self.execution, 'cleanup_status', 1)
        result = self.run_debug()
        self.cleanup.assert_called_once_with(self.execution, force_cleanup=False)
        self.execution.refresh_from_db.assert_called_once_with(fields=['cleanup_status'])
        self.assertEqual(result['cleanup_status'], 1)
        self.assertEqual(self.execution.status, 1)

    def test_manual_and_none_strategies_do_not_trigger_deletion(self):
        for status in (3, 4):
            self.runner.resolve_execution_cleanup_status.return_value = status
            self.assertEqual(self.run_debug()['cleanup_status'], status)
        self.cleanup.assert_not_called()

    def test_non_forced_cleanup_keeps_manual_items_pending_without_deleting(self):
        item = N(id=9, cleanup_status=4, cleanup_strategy=2, cleanup_resources={})
        self.execution.cleanup_status, self.execution.status = 0, 1
        with patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecution.objects') as executions, \
                patch('src.apps.data_factory.services.cleanup.cleanup.DataFactoryExecutionItem.objects') as items, \
                patch.object(Cleanup, 'mark_pending_manual') as retain, \
                patch.object(Cleanup, 'cleanup_items_in_database_transaction') as delete, \
                patch.object(Persistence, 'save'), \
                patch('src.apps.data_factory.services.cleanup.cleanup.transaction.on_commit'):
            executions.get.return_value = self.execution
            items.select_related.return_value.filter.return_value.order_by.return_value = [item]
            result = Cleanup.cleanup_execution(7, force_cleanup=False, defer_resources=True)
        retain.assert_called_once_with(item)
        delete.assert_not_called()
        self.assertEqual(result['skipped'], 1)

    def test_cleanup_failure_does_not_relabel_successful_creation_or_replay(self):
        self.cleanup.side_effect = DataFactoryError(DATA_FACTORY_CLEANUP_COORDINATION_FAILED, value=('AUTO cleanup failed',))
        with self.assertRaises(DataFactoryError):
            self.run_debug()
        self.assertEqual(self.execution.status, 1)
        self.runner.cleanup_failed_execution.assert_not_called()
        self.cleanup.assert_called_once()
        self.failed_wait.assert_called_once_with(7)

    def test_recovery_requires_matching_original_owner_and_confirmed_end(self):
        self.execution.source_type, self.execution.status, self.execution.cleanup_status = 1, 1, 0
        self.execution.context = {EXECUTION_OWNER_CONTEXT_KEY: self.owner.model_dump()}
        with patch.object(Reconcile, 'owner_ended', return_value=False):
            with self.assertRaises(DataFactoryError):
                Schedule.validate_debug_recovery(self.execution, self.owner)
        with patch.object(Reconcile, 'owner_ended', return_value=True):
            Schedule.validate_debug_recovery(self.execution, self.owner)
            changed = self.owner.model_copy(update={'process_token': 'AUTO_NEW_OWNER'})
            with self.assertRaises(DataFactoryError):
                Schedule.validate_debug_recovery(self.execution, changed)
            self.execution.status = 3
            with self.assertRaises(DataFactoryError):
                Schedule.validate_debug_recovery(self.execution, self.owner)

    def test_ended_owner_recovery_freezes_identity_without_forced_cleanup(self):
        from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
        self.execution.source_type, self.execution.status, self.execution.cleanup_status = 1, 1, 0
        self.execution.context = {EXECUTION_OWNER_CONTEXT_KEY: self.owner.model_dump()}
        with patch.object(Persistence, 'lock_execution', return_value=self.execution), \
                patch.object(Reconcile, 'owner_ended', return_value=True), \
                patch.object(ExecutorTaskService, 'create_cleanup_task') as create:
            Schedule.enqueue_debug_recovery.__wrapped__(Schedule, self.execution.id)
        create.assert_called_once_with(7, force_cleanup=False, recovery_owner=self.owner)

    def test_recovery_does_not_touch_running_debug_owner_and_enqueues_only_confirmed_end(self):
        self.execution.source_type, self.execution.status, self.execution.cleanup_status = 1, 1, 0
        self.execution.context = {EXECUTION_OWNER_CONTEXT_KEY: self.owner.model_dump()}
        with patch('src.apps.data_factory.services.recovery.execution_recovery.DataFactoryExecution.objects') as objects, \
                patch.object(Recovery, 'recover_inline_cleanup', return_value=0), \
                patch.object(Recovery, 'reconcile_manual_cleanup_states', return_value={'pending': 0, 'resolved': 0}), \
                patch.object(Reconcile, 'reconcile', return_value={}), \
                patch.object(Cleanup, 'reconcile_verified_cleanup', return_value=False), \
                patch.object(Recovery, 'fail_unverified_cleanup') as fail, \
                patch.object(Reconcile, 'owner_ended', return_value=False) as ended, \
                patch.object(Schedule, 'enqueue_debug_recovery', return_value=N(status='pending')) as enqueue:
            objects.filter.return_value.exclude.return_value.filter.return_value.distinct.return_value.order_by.return_value.__getitem__.return_value = [self.execution]
            result = Recovery.recover()
            self.assertEqual(result['data_factory_recovery_deferred_count'], 1)
            enqueue.assert_not_called()
            fail.assert_not_called()
            ended.return_value = True
            result = Recovery.recover()
            self.assertEqual(result['data_factory_recovery_queued_count'], 1)
            enqueue.assert_called_once_with(7)
            fail.assert_not_called()

    def test_worker_rechecks_frozen_debug_owner_instead_of_report_owner(self):
        fixture = schedule_fixtures.CleanupScheduleTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.lease.payload = {'execution_id': 7, 'force_cleanup': False,
                                 'recovery_owner': self.owner.model_dump()}
        with patch.object(Schedule, 'validate_debug_recovery') as validate:
            Schedule.run_claimed_step(fixture.lease)
        validate.assert_called_once_with(fixture.execution, self.owner)

    def test_worker_rejects_mixed_report_or_force_in_debug_recovery(self):
        fixture = schedule_fixtures.CleanupScheduleTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.lease.payload = {'execution_id': 7, 'force_cleanup': True,
                                 'recovery_owner': self.owner.model_dump()}
        with Infrastructure.scope():
            Schedule.run_claimed_step(fixture.lease)
        fixture.mocks[4].assert_not_called()
        fixture.mocks[5].assert_not_called()
        fixture.mocks[6].assert_called_once()
