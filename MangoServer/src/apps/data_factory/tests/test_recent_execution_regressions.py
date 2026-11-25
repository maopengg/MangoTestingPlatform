import ast
from contextlib import nullcontext
from pathlib import Path
from threading import Barrier, Event
from time import sleep
from types import SimpleNamespace as N
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from pymysql.err import OperationalError
from sqlalchemy.exc import OperationalError as SqlOperationalError
from sqlalchemy import Column, Integer, MetaData, Table, text

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.cleanup import cleanup_schedule
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata as Metadata
from src.apps.data_factory.tests import test_failure_convergence as insertion_fixtures
from src.apps.data_factory.tests import test_postgres_execution_metadata as metadata_fixtures
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks
from src.apps.system.enums.executor import ExecutorTaskStatusEnum
from src.processes.scheduler.runner import ScheduleRunner


class ConfigurationReasonTests(SimpleTestCase):
    def test_wrong_primary_key_names_reason_and_fix_without_inserting(self):
        fixture = insertion_fixtures.FailureConvergenceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.entity.primary_key = 'business_id'
        with self.assertRaises(DataFactoryError) as caught:
            fixture.insert({'id': 1})
        self.assertEqual(caught.exception.code, 34006)
        self.assertIn('business_id', caught.exception.msg)
        self.assertIn('真实主键 id', caught.exception.msg)
        self.assertIn('请同步模型表结构', caught.exception.msg)
        self.assertNotIn('输出配置格式错误', caught.exception.msg)
        with fixture.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar_one(), 0)

    def test_cached_ddl_change_retains_table_and_specific_reason(self):
        fixture = metadata_fixtures.PostgresExecutionMetadataTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with Metadata.scope():
            Metadata.resolve(fixture.entity, fixture.target, fixture.engine)
            fixture.definition['columns'].append(['AUTO_CHANGED'])
            with self.assertRaises(DataFactoryError) as caught:
                Metadata.resolve(fixture.entity, fixture.target, fixture.engine)
        self.assertIn('example', caught.exception.msg)
        self.assertIn('同次执行中表结构已变化', caught.exception.msg)
        self.assertIn('请重新同步并核查已创建数据', caught.exception.msg)

    def test_preflight_primary_change_preserves_reason_and_never_generates_insert_payload(self):
        from src.apps.data_factory.services.execution.parts.persistence import DataFactoryRunnerPersistenceMixin
        from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
        fixture = insertion_fixtures.FailureConvergenceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        changed = Table('example_changed', MetaData(), Column('business_id', Integer, primary_key=True))
        generate = Mock(return_value={'id': 1})
        with patch.object(DataFactoryDatasource, 'get_worker_engine', return_value=(fixture.engine, True)), \
                patch.object(Metadata, 'resolve', side_effect=[(fixture.table, {}), (changed, {})]):
            with self.assertRaises(DataFactoryError) as caught:
                DataFactoryRunnerPersistenceMixin.insert(fixture.entity, fixture.database, {},
                    prepare_payload=generate, prepare_resources=lambda: None)
        self.assertIn('资源预检后真实主键与模型不一致', caught.exception.msg)
        self.assertIn('修正主键配置', caught.exception.msg)
        generate.assert_not_called()
        with fixture.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar_one(), 0)

    def test_missing_and_mid_reflection_metadata_preserve_specific_reasons(self):
        fixture = metadata_fixtures.PostgresExecutionMetadataTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for values, reason in (([None], '未读取到有效表结构'),
                               ([fixture.definition, {'relation': [2]}], '读取期间表结构已变化')):
            fixture.connection.execute.return_value.scalar_one_or_none.side_effect = values
            with Metadata.scope(), self.assertRaises(DataFactoryError) as caught:
                Metadata.resolve(fixture.entity, fixture.target, fixture.engine)
            self.assertIn(reason, caught.exception.msg)
            self.assertIn('example', caught.exception.msg)

    def test_config_error_calls_match_the_single_placeholder(self):
        root = Path(__file__).resolve().parents[1] / 'services'
        for path in root.rglob('*.py'):
            for call in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(call, ast.Call) or not call.args:
                    continue
                if not isinstance(call.args[0], ast.Name) or call.args[0].id != 'DATA_FACTORY_CONFIG_INVALID':
                    continue
                values = next((keyword.value for keyword in call.keywords if keyword.arg == 'value'), None)
                self.assertIsInstance(values, ast.Tuple, str(path))
                self.assertEqual(len(values.elts), 1, f'{path}:{call.lineno}')


class JsonFailureReasonTests(SimpleTestCase):
    def test_driver_and_wrapper_use_safe_json_reason_and_keep_determined_failure(self):
        driver = OperationalError(3141, 'AUTO_PRIVATE_JSON_PASSWORD')
        for error in (driver, SqlOperationalError('AUTO_PRIVATE_SQL', {'x': 'AUTO_PRIVATE_VALUE'}, driver)):
            self.assertTrue(Errors.confirmed_rejection(error))
            self.assertIn('JSON', Errors.audit_reason(error))
            with self.assertRaises(DataFactoryError) as caught:
                Errors.raise_sql_error(N(db_type=0, database_name='fixture', password=None), error)
            self.assertEqual(caught.exception.code, 34024)
            self.assertIn('3141', caught.exception.msg)
            self.assertIn('修正后重试', caught.exception.msg)
            self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)

    def test_connection_invalidation_still_overrides_confirmed_rejection(self):
        wrapper = SqlOperationalError('AUTO_PRIVATE_SQL', {}, OperationalError(3141, 'AUTO_PRIVATE_JSON'))
        wrapper.connection_invalidated = True
        self.assertFalse(Errors.confirmed_rejection(wrapper))

    def test_json_audit_failure_is_safe_determined_and_not_a_success(self):
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit, SqlExecutionAuditHandle
        record = N(request_id='AUTO_REQUEST', source_detail={}, slow_threshold_ms=1000)
        error = SqlOperationalError('AUTO_PRIVATE_SQL', {}, OperationalError(3141, 'AUTO_PRIVATE_JSON'))
        with patch.object(Audit, 'save_completion'), patch.object(Audit, 'notify_slow'):
            Audit.finish_failure(SqlExecutionAuditHandle(record, 0), error, 1)
        self.assertEqual(record.status, 'fail')
        self.assertFalse(record.source_detail['outcome_unknown'])
        self.assertIn('3141', record.error_message)
        self.assertNotIn('AUTO_PRIVATE', record.error_message)


class ObservationDispatchTests(SimpleTestCase):
    def test_reserved_consumer_filters_sql_phase_and_inline_tasks(self):
        with patch('src.apps.task_center.services.execution.executor_task.transaction.atomic', side_effect=lambda: nullcontext()), \
                patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as objects:
            query = objects.select_for_update.return_value.filter.return_value.filter.return_value
            query.filter.return_value.order_by.return_value.first.return_value = None
            self.assertIsNone(Tasks.claim_cleanup_task(observations_only=True))
            query.filter.assert_called_once_with(progress_data__sql_done=True)
            query.filter.return_value.order_by.assert_called_once_with('available_at', 'id')
            condition = str(objects.select_for_update.return_value.filter.return_value.filter.call_args.args[0])
            self.assertIn('synchronous', condition)
            objects.select_for_update.assert_called_once_with(skip_locked=True)

    def test_expired_observation_claim_keeps_generation_fencing(self):
        task = N(id=11, status=ExecutorTaskStatusEnum.RUNNING.value, payload={'execution_id': 7},
                 progress_data={'sql_done': True, 'generation': 2}, started_at=timezone.now(), save=Mock())
        with patch('src.apps.task_center.services.execution.executor_task.transaction.atomic', side_effect=lambda: nullcontext()), \
                patch('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects') as objects:
            objects.select_for_update.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = task
            lease = Tasks.claim_cleanup_task(observations_only=True)
        self.assertTrue(lease.recovered)
        self.assertEqual(lease.generation, 3)
        self.assertTrue(lease.progress['sql_done'])
        self.assertEqual(task.progress_data['claim_token'], lease.token)

    def test_independent_observations_run_concurrently_without_multiplying_probe_budget(self):
        leases = [N(task_id=i) for i in range(4)]
        barrier = Barrier(4)
        def run(lease):
            self.assertEqual(cleanup_schedule._probe_worker_budget.get(), 1)
            barrier.wait(timeout=3)
        with patch.object(Tasks, 'claim_cleanup_task', side_effect=leases) as claim, \
                patch.object(Schedule, 'run_claimed', side_effect=run) as execute, \
                patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DatasourceGovernorService.policy',
                      return_value=DatasourcePerformancePolicy(pool_size=4)):
            self.assertTrue(Schedule.run_next(observations_only=True))
        self.assertEqual(execute.call_count, 4)
        self.assertEqual(claim.call_count, 4)
        self.assertTrue(all(call.kwargs == {'observations_only': True} for call in claim.call_args_list))
        self.assertEqual(cleanup_schedule._probe_worker_budget.get(), 4)

    def test_failed_observation_does_not_abandon_other_claimed_work(self):
        barrier, finished = Barrier(2), []
        def run(lease):
            barrier.wait(timeout=3)
            if lease.task_id == 1:
                raise RuntimeError('AUTO observation interrupted')
            sleep(0.02)
            finished.append(lease.task_id)
        with patch.object(Tasks, 'claim_cleanup_task', side_effect=[N(task_id=1), N(task_id=2)]), \
                patch.object(Schedule, 'run_claimed', side_effect=run), \
                patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DatasourceGovernorService.policy',
                      return_value=DatasourcePerformancePolicy(pool_size=2)):
            with self.assertRaises(RuntimeError):
                Schedule.run_next(observations_only=True)
        self.assertEqual(finished, [2])

    def test_mixed_consumer_still_claims_sql_tasks(self):
        with patch.object(Tasks, 'claim_cleanup_task', return_value=N(task_id=1)) as claim, \
                patch.object(Schedule, 'run_claimed') as execute:
            self.assertTrue(Schedule.run_next())
        claim.assert_called_once_with()
        execute.assert_called_once()

    def test_resizing_to_one_consumer_restores_mixed_mode_without_extra_threads(self):
        for count in (1, 2):
            runner = ScheduleRunner(cleanup_only=True)
            with patch('src.processes.scheduler.runner.threading.Thread') as threads, \
                    patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                          return_value=DatasourcePerformancePolicy(cleanup_consumer_threads=count)), \
                    patch.object(Schedule, 'run_next', side_effect=lambda **kwargs: runner.stop_event.set() or True) as run:
                runner.start_cleanup_consumers()
                self.assertEqual(threads.call_count, count)
                first = threads.call_args_list[0]
                first.kwargs['target'](*first.kwargs['args'])
                run.assert_called_once_with(observations_only=count > 1)

    def test_observation_consumer_progresses_while_bulk_sql_consumer_is_busy(self):
        runner = ScheduleRunner(cleanup_only=True)
        busy, released, observed = Event(), Event(), Event()
        def run(*, observations_only=False):
            if observations_only:
                if busy.is_set() and not released.is_set():
                    observed.set()
            else:
                busy.set()
                released.wait(3)
            return True
        with patch.object(Schedule, 'run_next', side_effect=run), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                      return_value=DatasourcePerformancePolicy(cleanup_consumer_threads=2)):
            try:
                runner.start_cleanup_consumers()
                self.assertTrue(busy.wait(2))
                self.assertTrue(observed.wait(2), 'SQL phase must not occupy every observation consumer')
                self.assertFalse(released.is_set())
            finally:
                released.set()
                runner.stop_event.set()
                for thread in runner.cleanup_threads:
                    thread.join(timeout=3)
            self.assertTrue(all(not thread.is_alive() for thread in runner.cleanup_threads))
