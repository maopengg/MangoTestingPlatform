from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.test import SimpleTestCase
from django.utils import timezone
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, func

from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_CONFIG_INVALID
from src.apps.data_factory.models import Database
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.cleanup import DataFactoryCleanup as Cleanup
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.datasource_pool import DatasourceQueuePool
from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.execution_snapshot import DATA_FACTORY_INSERT_SNAPSHOT_KEY
from src.apps.data_factory.services.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService as Audit, SqlExecutionAuditHandle
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore
from src.apps.data_factory.tests.test_datasource_audit import record


class SqlTransactionBudgetTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.policy = DatasourcePerformancePolicy()
        self.engine = create_engine('sqlite:///:memory:')
        self.addCleanup(self.engine.dispose)
        self.table = Table('example', MetaData(), Column('id', Integer, primary_key=True, autoincrement=True),
                           Column('name', String(32)))
        self.table.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(self.table.insert(), [{'name': f'AUTO_{index}'} for index in range(12)])
            ids = list(connection.execute(select(self.table.c.id)).scalars())
        self.database = Database(id=1, db_type=0, host='mysql.example.com', port=3306,
                                 display_name='example', extra_config={}, update_time=timezone.now())
        self.snapshot = {'version': 2, 'database_id': 1, 'connection_version': self.database.update_time.isoformat(),
                         'database_name': 'example', 'schema_name': '', 'redis_db': None,
                         'table_name': 'example', 'primary_key': 'id'}
        self.target = DatasourceTargetService.from_snapshot(self.database, self.snapshot)
        self.execution = SimpleNamespace(id=3, execution_no='DFEXAMPLE', source_type=4, source_id=9,
                                        stage=2, project_product_id=7)
        self.entity = SimpleNamespace(id=1, table_name='example', primary_key='id')
        self.items = [SimpleNamespace(id=index + 1, primary_value=str(value), data={'id': value},
                                      database=self.database, execution=self.execution, datasource_binding=None,
                                      template=SimpleNamespace(id=2, entity=self.entity), cleanup_resources={},
                                      insert_sql_params={DATA_FACTORY_INSERT_SNAPSHOT_KEY: self.snapshot}, save=Mock())
                      for index, value in enumerate(ids)]
        for method, value in (('policy', self.policy), ('store', self.store), ('lane', DatasourceQueueLaneEnum.CLEANUP)):
            guard = patch.object(Governor, method, return_value=value)
            guard.start()
            self.addCleanup(guard.stop)
        guard = patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext())
        guard.start()
        self.addCleanup(guard.stop)

        def advance_clock(seconds):
            self.store.now += seconds

        guard = patch('src.apps.data_factory.services.datasource_governor.time.sleep', side_effect=advance_clock)
        guard.start()
        self.addCleanup(guard.stop)
        self.records = []

        def start(**kwargs):
            value = record()
            value.id = len(self.records) + 1
            self.records.append(value)
            return SqlExecutionAuditHandle(value, kwargs['started_monotonic'])

        for method, kwargs in (('start', {'side_effect': start}), ('notify_slow', {})):
            guard = patch.object(Audit, method, **kwargs)
            guard.start()
            self.addCleanup(guard.stop)
        SqlDriverAuditService.attach(self.engine, self.target)

    def reflect(self, item, metadata, engine, target):
        if 'example' not in metadata.tables:
            self.table.to_metadata(metadata)
        return metadata.tables['example']

    def remaining_rows(self):
        with Governor.transaction_budget(self.target, 1):
            with self.engine.connect() as connection:
                return connection.execute(select(func.count()).select_from(self.table)).scalar_one()

    def test_large_cleanup_uses_bounded_transactions_and_tracks_every_committed_row(self):
        with patch.object(Cleanup, 'reflect_cleanup_table', side_effect=self.reflect), \
                patch.object(Cleanup, 'get_item_entity', return_value=self.entity), \
                patch('src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine',
                      return_value=(self.engine, True)):
            Cleanup.cleanup_items_in_database_transaction(self.items, allow_missing=True)
        self.assertEqual(self.remaining_rows(), 0)
        self.assertTrue(all(item.cleanup_resources['sql_cleaned'] for item in self.items))
        self.assertEqual(len(self.records), 25)

    def test_failure_after_prior_batch_keeps_prior_commit_evidence(self):
        original = Cleanup.delete_by_primary_key

        def fail_second_batch(item, **kwargs):
            if item.id == 5:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('fixture failure',))
            return original(item, **kwargs)

        with patch.object(Cleanup, 'reflect_cleanup_table', side_effect=self.reflect), \
                patch.object(Cleanup, 'delete_by_primary_key', side_effect=fail_second_batch), \
                patch.object(Cleanup, 'get_item_entity', return_value=self.entity), \
                patch('src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine',
                      return_value=(self.engine, True)), self.assertRaises(DataFactoryError):
            Cleanup.cleanup_items_in_database_transaction(self.items, allow_missing=True)
        self.assertEqual(self.remaining_rows(), 8)
        self.assertTrue(all(item.cleanup_resources.get('sql_cleaned') for item in self.items[:4]))
        self.assertTrue(all(not item.cleanup_resources.get('sql_cleaned') for item in self.items[4:]))

    def test_unplanned_extra_statement_is_metered_without_rejecting_valid_transaction(self):
        with Governor.transaction_budget(self.target, 2):
            with self.engine.begin() as connection:
                connection.execute(self.table.delete().where(self.table.c.id == 1))
                connection.execute(select(self.table.c.id)).first()
                connection.execute(select(self.table.c.id)).first()
        self.assertEqual(self.remaining_rows(), 11)
        self.assertTrue(all(not state['permits'] for state in self.store.values.values()))

    def test_thirty_concurrent_sql_fixtures_and_exact_cleanup_leave_zero_rows(self):
        # 实际执行本地 SQL、自动主键、精确 DELETE 与回查；不写任何远程业务库。
        with tempfile.TemporaryDirectory(prefix='mango-sql-queue-') as directory:
            engine = create_engine(f'sqlite:///{Path(directory) / "fixtures.db"}',
                                   poolclass=DatasourceQueuePool, pool_size=2, max_overflow=0,
                                   pool_timeout=0, connect_args={'check_same_thread': False, 'timeout': 10})
            try:
                self.table.metadata.create_all(engine)
                SqlDriverAuditService.attach(engine, self.target)
                clock_lock = threading.Lock()
                barrier = threading.Barrier(30)
                def pause(seconds=0.1):
                    with clock_lock:
                        self.store.now += seconds
                    # setUp 对 governor.time.sleep 的逻辑时钟桩会作用于 time 模块，
                    # 使用 Event 等待让操作线程真实交错，不能只串行跑完冒充并发。
                    threading.Event().wait(0.005)
                def case(index):
                    barrier.wait(timeout=5)
                    with Governor.transaction_budget(self.target, 2):
                        with engine.begin() as connection:
                            key = connection.execute(self.table.insert().values(name=f'AUTO_{index}')).inserted_primary_key[0]
                            self.assertEqual(connection.execute(select(self.table.c.name).where(
                                self.table.c.id == key)).scalar_one(), f'AUTO_{index}')
                    with Governor.transaction_budget(self.target, 2):
                        with engine.begin() as connection:
                            self.assertEqual(connection.execute(self.table.delete().where(
                                self.table.c.id == key)).rowcount, 1)
                            self.assertIsNone(connection.execute(select(self.table.c.id).where(
                                self.table.c.id == key)).first())
                    return index
                with patch.object(DatasourceWaitService, 'pause', side_effect=pause), \
                        ThreadPoolExecutor(max_workers=30) as executor:
                    futures = [executor.submit(case, index) for index in range(30)]
                    self.assertEqual(sorted(future.result(timeout=15) for future in futures), list(range(30)))
                with Governor.transaction_budget(self.target, 1):
                    with engine.connect() as connection:
                        self.assertEqual(connection.execute(select(func.count()).select_from(self.table)).scalar_one(), 0)
                permits = [value for state in self.store.values.values() for value in state['permits'].values()]
                self.assertTrue(all(value['kind'] == 'connection' for value in permits))
                self.assertLessEqual(sum(value['slots'] for value in permits), 2)
            finally:
                engine.dispose()
            self.assertTrue(all(not state['permits'] for state in self.store.values.values()))
