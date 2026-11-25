from collections import defaultdict
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone as datetime_timezone, timedelta
from types import SimpleNamespace as N
from threading import Lock
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_CLEANUP_TIMEOUT
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup import cleanup_schedule
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService as Persistence
from src.apps.data_factory.services.cleanup import cleanup_persistence
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.tests import test_cleanup_schedule as schedule_fixtures
from src.apps.data_factory.tests import test_factory_reliability_regressions as resource_fixtures
from src.apps.task_center.models import WorkbenchTodo
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks
from src.apps.task_center.services.workbench.todo import WorkbenchTodoService as Todos


class VirtualClock:
    def __init__(self):
        self.value = 1800000000.0
        self.lock = Lock()

    def now(self):
        with self.lock:
            return datetime.fromtimestamp(self.value, datetime_timezone.utc)

    def advance(self, duration):
        with self.lock:
            self.value += duration
            if self.value > 1800001200:
                raise AssertionError('AUTO bounded virtual execution exceeded')


class InlineBulkObservationTests(SimpleTestCase):
    def setUp(self):
        real_advance, real_initialize = Resources.advance, Resources.initialize_observation
        self.fixture = schedule_fixtures.CleanupScheduleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        resource = resource_fixtures.LateEsRecoveryTests()
        resource.setUp()
        self.addCleanup(resource.doCleanups)
        self.resource = resource
        self.clock, self.loads, self.samples = VirtualClock(), 0, defaultdict(list)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.fixture.lease.payload = {'execution_id': 7, 'mode': 'synchronous'}
        for key, value in vars(resource.item.execution).items():
            setattr(self.fixture.execution, key, value)
        self.fixture.execution.status = 1
        self.fixture.execution.error_message = None
        resource.snapshot.rule.timeout_seconds = 30
        resource.state.snapshots = [resource.snapshot]
        resource.item.cleanup_resources = resource.state.model_dump(mode='json')
        self.es_items = [deepcopy(resource.item) for _ in range(101)]
        for index, item in enumerate(self.es_items):
            item.id, item.cleanup_status = index + 1000, 2
            item.cleanup_strategy = 1
            item.execution = self.fixture.execution
            item.cleanup_resources['snapshots'][0]['document_id'] = str(item.id)
        self.items = [N(id=index + 2000, cleanup_status=1, cleanup_strategy=1,
                        cleanup_resources=CleanupResourceState(sql_cleaned=True).model_dump(mode='json'))
                      for index in range(101)] + self.es_items
        fixture = self
        class LoadedItems:
            def __iter__(self):
                fixture.loads += 1
                fixture.clock.advance(8)
                return iter(fixture.items)
        self.rows = LoadedItems()
        self.fixture.mocks[-1].select_related.return_value.filter.return_value.order_by.return_value = self.rows
        self.fixture.mocks[-1].select_for_update.return_value.filter.return_value = self.items
        self.fixture.mocks[8].side_effect = real_advance
        self.fixture.mocks[11].side_effect = real_initialize
        self.fixture.mocks[10].side_effect = self.clock.now
        self.fixture.mocks[9].return_value = DatasourcePerformancePolicy(pool_size=1)
        self.fixture.mocks[6].side_effect = self.record_failure
        resource.sample.side_effect = self.sample
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_schedule.monotonic',
                                       side_effect=lambda: self.clock.value))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_schedule.sleep',
                                       side_effect=self.clock.advance))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_resource.logger.debug'))
        self.stack.enter_context(patch('src.apps.data_factory.services.cleanup.cleanup_resource.logger.warning'))

    def sample(self, snapshot, *args, **kwargs):
        self.samples[snapshot.document_id].append(self.clock.value)
        self.clock.advance(0.1)
        return True

    def record_failure(self, execution, message):
        execution.cleanup_status, execution.error_message = 2, message

    def run_inline(self):
        Schedule.run_inline(self.fixture.lease)

    def test_old_repeated_load_path_reproduces_restart_and_300_second_timeout(self):
        with patch.object(Schedule, 'observation_items', side_effect=lambda *args, **kwargs: list(self.rows)):
            self.run_inline()
        self.assertEqual(self.fixture.execution.cleanup_status, 2)
        self.assertIn(DATA_FACTORY_CLEANUP_TIMEOUT.message, self.fixture.execution.error_message)
        self.assertGreater(self.loads, 10)
        self.assertGreater(self.fixture.lease.progress['es_seconds'], 300)
        self.assertTrue(any((item.cleanup_resources.get('checkpoints') or [{}])[0].get('restart_count', 0) > 2
                            for item in self.es_items))

    def test_101_es_resources_complete_through_real_inline_loop_with_loading_overhead(self):
        self.run_inline()
        self.assertEqual(self.fixture.execution.cleanup_status, 1)
        self.assertEqual(self.loads, 1)
        self.assertLess(self.fixture.lease.progress['es_seconds'], 300)
        self.assertEqual(self.fixture.mocks[5].call_count, 101)
        self.fixture.mocks[4].assert_called_once()
        self.fixture.mocks[0].assert_not_called()
        self.fixture.mocks[-1].select_for_update.assert_called_once()
        starts = []
        for item in self.es_items:
            self.assertEqual(item.cleanup_status, 1)
            state = Resources.state(item)
            check = state.checkpoints[0]
            starts.append(check.started_at)
            self.assertEqual(check.restart_count, 0)
            self.assertGreaterEqual(check.last_checked_at - check.started_at, 30)
            self.assertGreaterEqual(check.final_count, 2)
            self.assertGreaterEqual(check.absent_count, 2)
            self.assertEqual(len(state.results), 1)
        self.assertGreater(starts[-1] - starts[0], 30, 'queued resources must get a new full observation window')
        self.assertIsNone(cleanup_schedule._inline_observation_items.get())

    def test_unbounded_admission_without_reload_still_exceeds_budget(self):
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.ES_CLEANUP_PROBE_BATCH_SIZE', 101), \
                patch('src.apps.data_factory.services.cleanup.cleanup_schedule.ES_CLEANUP_RESOURCES_PER_WORKER', 101):
            self.run_inline()
        self.assertEqual(self.loads, 1)
        self.assertEqual(self.fixture.execution.cleanup_status, 2)
        self.assertGreater(self.fixture.lease.progress['es_seconds'], 300)
        self.assertIn(DATA_FACTORY_CLEANUP_TIMEOUT.message, self.fixture.execution.error_message)

    def test_101_resources_complete_with_two_parallel_probe_workers(self):
        self.fixture.mocks[9].return_value = DatasourcePerformancePolicy(pool_size=2)
        self.run_inline()
        self.assertEqual(self.fixture.execution.cleanup_status, 1)
        self.assertEqual(self.loads, 1)
        for item in self.es_items:
            state = Resources.state(item)
            self.assertEqual(item.cleanup_status, 1)
            self.assertEqual(state.checkpoints[0].restart_count, 0)
            self.assertGreaterEqual(state.checkpoints[0].last_checked_at - state.checkpoints[0].started_at, 30)
            self.assertGreaterEqual(state.checkpoints[0].final_count, 2)

    def test_persisted_proof_is_rechecked_even_if_in_memory_resources_all_completed(self):
        unverified = N(id=9999, cleanup_status=1, cleanup_resources={})
        self.fixture.mocks[-1].select_for_update.return_value.filter.return_value = [unverified]
        self.run_inline()
        self.assertTrue(all(item.cleanup_status == 1 for item in self.es_items))
        self.assertEqual(self.fixture.execution.cleanup_status, 2)
        self.assertIn('缺少完整成功证据', self.fixture.execution.error_message)

    def test_ownership_mismatch_still_refuses_delete_in_inline_working_set(self):
        from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
        self.resource.sample.side_effect = self.resource.real_sample
        def document(target, index, identity, **kwargs):
            self.assertFalse(kwargs.get('delete', False))
            return {'_index': index, '_id': identity, '_source': {'tenantId': '8'},
                    '_seq_no': 1, '_primary_term': 1}
        with patch.object(ES, 'resolve_index', return_value=('example', 'AUTO_UUID')), \
                patch.object(ES, 'document', side_effect=document) as requests:
            self.run_inline()
        self.assertEqual(self.fixture.execution.cleanup_status, 2)
        self.assertTrue(requests.called)
        self.fixture.mocks[5].assert_not_called()

    def test_verify_mode_with_existing_document_cannot_report_success(self):
        self.es_items[0].cleanup_resources['snapshots'][0]['rule']['mode'] = 'verify'
        def sample(snapshot, *args, **kwargs):
            self.clock.advance(0.1)
            return snapshot.document_id != str(self.es_items[0].id)
        self.resource.sample.side_effect = sample
        self.run_inline()
        self.assertEqual(self.fixture.execution.cleanup_status, 2)
        self.assertEqual(Resources.state(self.es_items[0]).results, [])

    def test_cached_items_are_fenced_by_token_generation_and_execution(self):
        token = cleanup_schedule._inline_observation_items.set({})
        lease = self.fixture.lease
        try:
            Schedule.observation_items(7, lease, inline=True)
            Schedule.observation_items(7, lease, inline=True)
            self.assertEqual(self.loads, 1)
            lease.token = 'AUTO_NEW_TOKEN'
            Schedule.observation_items(7, lease, inline=True)
            lease.generation += 1
            Schedule.observation_items(7, lease, inline=True)
            Schedule.observation_items(8, lease, inline=True)
            self.assertEqual(self.loads, 4)
            Schedule.observation_items(8, lease, inline=False)
            self.assertEqual(self.loads, 5)
        finally:
            cleanup_schedule._inline_observation_items.reset(token)


class InlineLeaseTests(SimpleTestCase):
    def test_waiting_keeps_lease_checks_and_stops_after_owner_replaced(self):
        clock = VirtualClock()
        lease = N(task_id=3, generation=0)
        with patch.object(Schedule, 'run_claimed', return_value=clock.value + 3) as run, \
                patch.object(Schedule, 'server_now', side_effect=clock.now), \
                patch('src.apps.data_factory.services.cleanup.cleanup_schedule.sleep', side_effect=clock.advance), \
                patch.object(Tasks, 'with_cleanup_lease', side_effect=[(True, True), (False, None)]) as check, \
                Infrastructure.scope():
            with self.assertRaises(DataFactoryError):
                Schedule.run_inline(lease)
        self.assertEqual(check.call_count, 2)
        self.assertIs(check.call_args.args[0], lease)
        run.assert_called_once()
        self.assertIsNone(cleanup_schedule._inline_observation_items.get())
        self.assertIsNone(cleanup_persistence._cleanup_lease.get())


class CleanupMailSummaryTests(SimpleTestCase):
    def setUp(self):
        fixture = resource_fixtures.LateEsRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.now = timezone.now() - timedelta(minutes=10)
        self.execution = N(id=7, cleanup_time=self.now, update_time=self.now,
                           error_message=DATA_FACTORY_CLEANUP_TIMEOUT.message)
        self.items = [N(cleanup_status=1, cleanup_resources={'sql_cleaned': True}) for _ in range(101)]
        for index in range(101):
            state = deepcopy(fixture.state)
            state.snapshots[0].document_id = str(index + 1)
            self.items.append(N(cleanup_status=2, cleanup_resources=state.model_dump(mode='json')))

    def test_202_items_distinguish_verified_sql_and_unverified_es(self):
        summary, counts = Todos.cleanup_notice_fields(self.execution, self.items)
        self.assertIn('共 202 项', summary)
        self.assertIn('已确认完整清理 101 项', summary)
        self.assertIn('SQL已记录清理完成、ES清理/验证未确认 101 项', summary)
        self.assertIn('处理超时', summary)
        self.assertIn('不要重跑Case', summary)
        self.assertNotIn('失败 101 项、成功 101 项', summary)
        self.assertEqual(counts['sql_cleaned_count'], 202)
        self.assertEqual(counts['es_unverified_count'], 101)
        self.assertEqual(counts['verified_count'], 101)
        self.assertEqual(counts['unverified_count'], 101)
        self.assertEqual(counts['sql_unverified_count'], 0)

    def test_missing_sql_proof_is_not_described_as_sql_cleaned(self):
        summary, counts = Todos.cleanup_notice_fields(self.execution, [N(cleanup_status=2, cleanup_resources={})])
        self.assertIn('SQL清理未确认 1 项', summary)
        self.assertNotIn('SQL已记录清理完成', summary)
        self.assertEqual(counts['sql_cleaned_count'], 0)

    def test_notification_rebuilds_stale_summary_and_counts_before_sending(self):
        todo = N(id=11, source_id=7, create_time=self.now, summary='AUTO_OLD_SUCCESS_0',
                 event_key=f'data-factory:execution:7:cleanup-failed:{Todos._timestamp_key(self.now)}',
                 details={'success_count': 0, 'failed_count': 202, 'original_evidence': 'AUTO_KEEP'}, save=Mock())
        def notify(current):
            self.assertIn('已确认完整清理 101 项', current.summary)
            self.assertEqual(current.details['success_count'], 101)
            self.assertEqual(current.details['failed_count'], 101)
            return True
        with patch.object(WorkbenchTodo.objects, 'select_for_update') as rows, \
                patch('src.apps.task_center.services.workbench.todo.DataFactoryExecution.objects.filter') as executions, \
                patch.object(Todos, '_cleanup_items', return_value=self.items), \
                patch.object(Todos, '_notify_owner', side_effect=notify):
            rows.return_value.select_related.return_value.filter.return_value.first.return_value = todo
            executions.return_value.only.return_value.first.return_value = self.execution
            self.assertTrue(Todos._notify_cleanup_failure_if_due.__wrapped__(Todos, todo.id))
        self.assertEqual(todo.details['original_evidence'], 'AUTO_KEEP')
        self.assertIn('cleanup_notification_sent_at', todo.details)
        self.assertIn('summary', todo.save.call_args.kwargs['update_fields'])

    def test_reason_does_not_leak_driver_sql_or_credentials(self):
        self.execution.error_message = 'AUTO_PRIVATE_SQL password=AUTO_PRIVATE_PASSWORD'
        summary, _ = Todos.cleanup_notice_fields(self.execution, self.items)
        self.assertNotIn('AUTO_PRIVATE', summary)
