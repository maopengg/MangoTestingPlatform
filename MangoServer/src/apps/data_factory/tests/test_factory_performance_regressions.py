from contextlib import contextmanager, nullcontext
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, select, text
from sqlalchemy.pool import QueuePool

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, DatasourceTypeBudget
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.execution_metadata import DataFactoryExecutionMetadata as Metadata
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.services.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class RateSettlementTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.policy = DatasourcePerformancePolicy(mysql=DatasourceTypeBudget(
            concurrency=4, requests_per_second=20, connections=8, cleanup_reserved=1), pool_size=2)
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        for method, kwargs in (
            ('store', {'return_value': self.store}), ('policy', {'return_value': self.policy}),
            ('configuration_guard', {'side_effect': lambda *args: nullcontext()}),
        ):
            guard = patch.object(Governor, method, **kwargs)
            guard.start()
            self.addCleanup(guard.stop)

    def state(self):
        return next(iter(self.store.values.values()))

    def execute(self, count):
        for _ in range(count):
            with Governor.operation(self.target, physical=True):
                pass

    def test_four_sql_charge_four_not_sixteen_tokens(self):
        with Governor.transaction_budget(self.target, 8):
            self.execute(1)
        with Governor.transaction_budget(self.target, 8):
            self.execute(3)
        self.assertEqual(self.state()['tokens'], 16)
        self.assertEqual(self.state()['normal_tokens'], 11)
        self.assertFalse(self.state()['permits'])

    def test_unsent_sql_returns_entire_reservation(self):
        with self.assertRaisesRegex(RuntimeError, 'AUTO_BEFORE_SEND'):
            with Governor.transaction_budget(self.target, 8):
                raise RuntimeError('AUTO_BEFORE_SEND')
        self.assertEqual(self.state()['tokens'], 20)
        self.assertEqual(self.state()['normal_tokens'], 15)

    def test_sent_failure_is_charged_but_unused_tokens_return(self):
        with self.assertRaisesRegex(RuntimeError, 'AUTO_SQL_FAILURE'):
            with Governor.transaction_budget(self.target, 8):
                with Governor.operation(self.target, physical=True):
                    raise RuntimeError('AUTO_SQL_FAILURE')
        self.assertEqual(self.state()['tokens'], 19)
        self.assertEqual(self.state()['normal_tokens'], 14)
        self.assertFalse(self.state()['permits'])

    def test_admission_failure_does_not_consume_credit_for_unsent_statement(self):
        with Governor.transaction_budget(self.target, 8):
            with patch.object(Governor, 'acquire', side_effect=RuntimeError('AUTO_NOT_SENT')):
                with self.assertRaisesRegex(RuntimeError, 'AUTO_NOT_SENT'):
                    self.execute(1)
        self.assertEqual(self.state()['tokens'], 20)

    def test_extra_sql_still_consumes_normal_rate(self):
        with Governor.transaction_budget(self.target, 2):
            self.execute(4)
        self.assertEqual(self.state()['tokens'], 16)
        self.assertFalse(self.state()['permits'])

    def test_cleanup_refund_cannot_expand_normal_capacity(self):
        from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            with Governor.transaction_budget(self.target, 8):
                self.execute(1)
        self.assertEqual(self.state()['tokens'], 19)
        self.assertEqual(self.state()['normal_tokens'], 15)

    def test_refund_lost_reply_is_not_retried_or_reported_as_case_failure(self):
        with Governor.transaction_budget(self.target, 8):
            self.execute(1)
            original = self.store.atomic_update
            def committed_then_disconnected(*args, **kwargs):
                original(*args, **kwargs)
                raise ConnectionError('AUTO_LOST_REPLY')
            guard = patch.object(self.store, 'atomic_update', side_effect=committed_then_disconnected)
            refund = guard.start()
        guard.stop()
        self.assertEqual(refund.call_count, 1)
        self.assertEqual(self.state()['tokens'], 19)

    def test_concurrent_reservations_settle_only_their_own_unused_credits(self):
        barrier = threading.Barrier(2)
        def run(_):
            with Governor.transaction_budget(self.target, 4):
                barrier.wait(timeout=5)
                self.execute(1)
        with ThreadPoolExecutor(max_workers=2) as workers:
            list(workers.map(run, range(2)))
        self.assertEqual(self.state()['tokens'], 18)
        self.assertEqual(self.state()['normal_tokens'], 13)
        self.assertFalse(self.state()['permits'])


class ExecutionMetadataTests(SimpleTestCase):
    ddl = 'CREATE TABLE `example` (\n `id` bigint NOT NULL AUTO_INCREMENT,\n PRIMARY KEY (`id`)\n) ENGINE=InnoDB AUTO_INCREMENT=10'

    def setUp(self):
        self.target = SimpleNamespace(cache_key='binding-1-version-1', schema_name='example')
        self.entity = SimpleNamespace(table_name='example', primary_key='id')
        self.engine = Mock()
        self.engine.dialect.name = 'mysql'
        self.engine.connect.return_value = nullcontext(Mock())
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True))

    def test_reuses_reflection_but_still_reads_fresh_ddl_before_every_insert(self):
        with patch('src.apps.data_factory.services.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl) as ddl, Metadata.scope():
            for _ in range(28):
                table, kinds = Metadata.resolve(self.entity, self.target, self.engine)
                self.assertIs(table, self.table)
                self.assertEqual(kinds, {'id': 'auto_increment'})
            self.assertEqual(reflect.call_count, 1)
            self.assertEqual(ddl.call_count, 29)

    def test_counter_changes_do_not_hide_real_structural_changes(self):
        with patch('src.apps.data_factory.services.execution_metadata.Table', return_value=self.table), \
                patch('src.apps.data_factory.services.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      side_effect=[self.ddl, self.ddl, self.ddl.replace('=10', '=11'),
                                   self.ddl.replace('bigint', 'varchar(32)')]), Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine)
            Metadata.resolve(self.entity, self.target, self.engine)
            with self.assertRaises(DataFactoryError):
                Metadata.resolve(self.entity, self.target, self.engine)

    def test_quoted_literals_are_not_normalized(self):
        self.assertNotEqual(Metadata.definition_signature(self.ddl + " COMMENT='AUTO_INCREMENT=10'"),
                            Metadata.definition_signature(self.ddl + " COMMENT='AUTO_INCREMENT=11'"))

    def test_binding_versions_and_executions_do_not_share_tables(self):
        with patch('src.apps.data_factory.services.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl):
            with Metadata.scope():
                Metadata.resolve(self.entity, self.target, self.engine)
                Metadata.resolve(self.entity, SimpleNamespace(cache_key='binding-2', schema_name='example'), self.engine)
            with Metadata.scope():
                Metadata.resolve(self.entity, self.target, self.engine)
            self.assertEqual(reflect.call_count, 3)

    def test_schema_changes_during_initial_reflection_reject_insert(self):
        with patch('src.apps.data_factory.services.execution_metadata.Table', return_value=self.table), \
                patch('src.apps.data_factory.services.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      side_effect=[self.ddl, self.ddl.replace('bigint', 'varchar(32)')]), Metadata.scope():
            with self.assertRaises(DataFactoryError):
                Metadata.resolve(self.entity, self.target, self.engine)

    def test_supplied_connection_is_reused_for_both_ddl_reads_and_reflection(self):
        connection = Mock()
        with patch('src.apps.data_factory.services.execution_metadata.Table', return_value=self.table) as reflect, \
                patch('src.apps.data_factory.services.execution_metadata.DataFactoryDiscover.get_mysql_table_definition',
                      return_value=self.ddl) as ddl, Metadata.scope():
            Metadata.resolve(self.entity, self.target, self.engine, connection=connection)
            self.engine.connect.assert_not_called()
            self.assertIs(reflect.call_args.kwargs['autoload_with'], connection)
            self.assertEqual([call.args[0] for call in ddl.call_args_list], [connection, connection])


class LatePayloadTests(SimpleTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=0.1)
        self.addCleanup(self.engine.dispose)
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True),
                           Column('name', String(32)), Column('requested', DateTime))
        self.table.metadata.create_all(self.engine)
        self.entity = SimpleNamespace(table_name='example', primary_key='id', unique_key='')
        self.target = SimpleNamespace(schema_name='', db_type=DataSourceTypeEnum.SQLITE.value)

    def test_payload_is_built_once_after_structure_budget_and_pool_wait(self):
        now = [datetime(2026, 1, 1, 12)]
        @contextmanager
        def budget(*_):
            now[0] += timedelta(minutes=4)
            yield
        prepare = Mock(side_effect=lambda: {'name': 'AUTO_LATE', 'requested': now[0] - timedelta(minutes=10)})
        with patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                patch.object(Governor, 'transaction_budget', side_effect=budget):
            result = DataFactoryRunner.insert(self.entity, self.target, {}, prepare_payload=prepare)
        prepare.assert_called_once()
        self.assertEqual(result['created']['requested'], datetime(2026, 1, 1, 11, 54))
        self.assertGreater(result['created']['id'], 0)

    def test_payload_or_preflight_failure_creates_no_business_row(self):
        with patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                patch.object(Governor, 'transaction_budget', side_effect=lambda *_: nullcontext()), \
                self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(self.entity, self.target, {},
                prepare_payload=Mock(side_effect=RuntimeError('AUTO_PREFLIGHT_FAILURE')))
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table)).all(), [])

    def test_one_connection_pool_inserts_and_returns_connection_without_nested_checkout(self):
        with patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                patch.object(Governor, 'transaction_budget', side_effect=lambda *_: nullcontext()):
            for number in range(3):
                DataFactoryRunner.insert(self.entity, self.target, {'name': f'AUTO_POOL_{number}'})
                self.assertEqual(self.engine.pool.checkedout(), 0)
        with self.engine.connect() as connection:
            self.assertEqual(len(connection.execute(select(self.table)).all()), 3)

    def test_invalid_primary_key_blocks_payload_generation_and_insert(self):
        prepare = Mock(return_value={'name': 'AUTO_UNSAFE'})
        self.entity.primary_key = 'not_the_primary_key'
        with patch('src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine',
                   return_value=(self.engine, True)), \
                patch.object(Governor, 'transaction_budget', side_effect=lambda *_: nullcontext()), \
                self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(self.entity, self.target, {}, prepare_payload=prepare)
        prepare.assert_not_called()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(select(self.table)).all(), [])

    def test_pre_admission_wait_is_recorded_without_inflating_sql_duration(self):
        handle = SqlExecutionAuditHandle(SimpleNamespace(source_detail={}), 0,
                                        wait_started=10, admission_wait_ms=700)
        with patch('src.apps.data_factory.services.sql_execution_audit.DatasourceWaitService.elapsed', return_value=10.2):
            duration = Audit.measured_duration(handle, 300)
        self.assertEqual(duration, 100)
        self.assertEqual(handle.record.source_detail['resource_wait_ms'], 900)

    def test_physical_driver_captures_wait_before_audit_starts(self):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService, _wait_elapsed
        handles = []
        @contextmanager
        def admission(*_, **__):
            _wait_elapsed.set(_wait_elapsed.get() + 0.7)
            yield {'admission_wait_ms': 700}
        def start(**kwargs):
            record = SimpleNamespace(id=1, status='running', request_id='AUTO_WAIT', source_detail={},
                                     source_stage='statement', slow_threshold_ms=20000, save=Mock())
            handle = SqlExecutionAuditHandle(record, kwargs['started_monotonic'])
            handles.append(handle)
            return handle
        # 连接已预热；本测试只覆盖真实 cursor 事件，不调用网络或控制库。
        SqlDriverAuditService.attach(self.engine, SimpleNamespace(id=1, db_type=DataSourceTypeEnum.SQLITE.value))
        with DatasourceWaitService.owner(None), patch.object(Governor, 'operation', side_effect=admission), \
                patch.object(Audit, 'start', side_effect=start), patch.object(Audit, 'notify_slow'):
            with self.engine.connect() as connection:
                self.assertEqual(connection.execute(text('SELECT 1')).scalar_one(), 1)
        self.assertEqual(len(handles), 1)
        self.assertEqual(handles[0].record.source_detail['resource_wait_ms'], 700)
        self.assertFalse(handles[0].record.is_slow)
