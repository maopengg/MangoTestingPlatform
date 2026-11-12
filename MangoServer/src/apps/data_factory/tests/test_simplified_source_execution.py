import os
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import create_engine, text

from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.pool.datasource_pool import DatasourceQueuePool
from src.apps.data_factory.services.sql.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class SimplifiedSourceExecutionTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.target = SimpleNamespace(id=49, db_type=0, host='mysql.example.com', port=3306)
        self.records = []
        self.lock = threading.Lock()
        self.folder = tempfile.TemporaryDirectory(prefix='mango-connection-regression-')
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'fixture.sqlite'
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy(pool_size=2)),
                patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                patch.object(Governor, '_closed_connections', set()),
                patch.object(Governor, '_pending_releases', set()),
                patch.object(Governor, '_closed_pid', os.getpid()),
                patch.object(Audit, 'start', side_effect=self.audit), patch.object(Audit, 'notify_slow')):
            guard.start()
            self.addCleanup(guard.stop)
        self.engine = create_engine('sqlite://', poolclass=DatasourceQueuePool, pool_size=2,
            max_overflow=0, pool_timeout=0, creator=lambda: GovernedDbapiConnection.connect(
                self.target, lambda: sqlite3.connect(self.path, check_same_thread=False, timeout=10)))
        self.addCleanup(self.engine.dispose)
        SqlDriverAuditService.attach(self.engine, self.target)
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE fixture(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)'))

    def audit(self, **kwargs):
        with self.lock:
            record = SimpleNamespace(id=len(self.records)+1, database_id=49, datasource_type=0,
                request_id=f'request-{len(self.records)+1}', status='running', source_detail={},
                source_stage='statement', slow_threshold_ms=20000, duration_ms=0, save=Mock(),
                statement=kwargs['sql'])
            self.records.append(record)
        return SqlExecutionAuditHandle(record, time.perf_counter())

    def test_hundred_cases_use_case_concurrency_and_exact_cleanup_without_sql_quota(self):
        slots = threading.Semaphore(10)
        active = peak = 0
        expected_failures = []
        def case(index):
            nonlocal active, peak
            with slots:
                with self.lock:
                    active += 1
                    peak = max(peak, active)
                key = None
                try:
                    with self.engine.begin() as connection:
                        key = connection.execute(text('INSERT INTO fixture(name) VALUES(:name)'),
                            {'name': f'AUTO_{index}'}).lastrowid
                        self.assertEqual(connection.execute(text('SELECT name FROM fixture WHERE id=:id'),
                            {'id': key}).scalar_one(), f'AUTO_{index}')
                    time.sleep(0.001)
                    if index % 11 == 0:
                        expected_failures.append(index)
                        raise AssertionError('controlled business assertion failure')
                except AssertionError as error:
                    if str(error) != 'controlled business assertion failure':
                        raise
                finally:
                    if key is not None:
                        with self.engine.begin() as connection:
                            self.assertEqual(connection.execute(text('DELETE FROM fixture WHERE id=:id'), {'id': key}).rowcount, 1)
                            self.assertIsNone(connection.execute(text('SELECT id FROM fixture WHERE id=:id'), {'id': key}).first())
                    with self.lock:
                        active -= 1
        with ThreadPoolExecutor(max_workers=30) as workers:
            list(workers.map(case, range(100)))
        self.assertLessEqual(peak, 10)
        self.assertGreater(peak, 2)
        self.assertEqual(len(expected_failures), 10)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar_one(), 0)
        self.assertFalse(hasattr(Governor, 'operation'))
        self.assertFalse(hasattr(Governor, 'transaction_budget'))
        state = next(value for key, value in self.store.values.items() if key.startswith('group:'))
        self.assertNotIn('tokens', state)
        self.assertNotIn('waiters', state)
        self.assertTrue(all(value['kind'] == 'connection' for value in state['permits'].values()))
        self.engine.dispose()
        self.assertFalse(next(value for key, value in self.store.values.items() if key.startswith('group:'))['permits'])

    def test_sent_write_timeout_is_not_replayed_and_new_operations_are_not_quota_blocked(self):
        original = self.engine.dialect.do_execute
        writes = []
        def lost_response(cursor, statement, parameters, context):
            result = original(cursor, statement, parameters, context)
            if statement.startswith('INSERT'):
                writes.append(statement)
                cursor.connection.commit()
                raise TimeoutError('write response lost')
            return result
        with patch.object(self.engine.dialect, 'do_execute', side_effect=lost_response):
            with self.assertRaises(TimeoutError):
                with self.engine.begin() as connection:
                    connection.execute(text('INSERT INTO fixture(name) VALUES(:name)'), {'name': 'AUTO_RESPONSE_LOST'})
        self.assertEqual(len(writes), 1)
        self.assertTrue(any(record.source_detail.get('outcome_unknown') for record in self.records))
        # 测试夹具明确知道本次唯一键，独立回查后精确清理；生产链路不能盲目重放INSERT。
        with self.engine.begin() as connection:
            key = connection.execute(text('SELECT id FROM fixture WHERE name=:name'), {'name': 'AUTO_RESPONSE_LOST'}).scalar_one()
            self.assertEqual(connection.execute(text('DELETE FROM fixture WHERE id=:id'), {'id': key}).rowcount, 1)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar_one(), 0)
