import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, DatasourceTypeBudget
from src.apps.data_factory.services.datasource_cost import DatasourceCostService
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor


class AtomicMemoryStore:
    def __init__(self):
        self.values = {}
        self.now = 1_800_000_000
        self.lock = threading.Lock()
        self.using = 'unit'

    def control_connection(self):
        return nullcontext()

    def atomic_update(self, key, transform, ttl=None, utc_clock=False):
        with self.lock:
            value, result = transform(copy.deepcopy(self.values.get(key)), datetime.fromtimestamp(self.now, timezone.utc))
            self.values[key] = copy.deepcopy(value)
            return result


class DatasourcePerformanceTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        pending = patch.object(Governor, '_pending_releases', set())
        pending.start()
        self.addCleanup(pending.stop)
        # 固定用户已有的保守配置，验证新默认值不影响旧配置下的准入与恢复。
        self.policy = DatasourcePerformancePolicy(mysql=DatasourceTypeBudget(
            concurrency=4, requests_per_second=20, connections=8, cleanup_reserved=1, metadata_per_second=1),
            pool_size=2, max_waiters=100)
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        guard = patch.object(Governor, 'configuration_guard', side_effect=lambda using, expected=None: nullcontext())
        guard.start()
        self.addCleanup(guard.stop)
        for method, value in [('store', self.store), ('policy', self.policy),
                              ('lane', DatasourceQueueLaneEnum.NORMAL)]:
            mock = patch.object(Governor, method, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_cross_thread_normal_and_cleanup_share_hard_capacity(self):
        def acquire(_):
            try:
                return Governor.acquire(self.target, wait=False)
            except DataFactoryError:
                return None
        with ThreadPoolExecutor(max_workers=12) as executor:
            permits = [permit for permit in executor.map(acquire, range(12)) if permit]
        self.assertEqual(len(permits), 3)
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            cleanup = Governor.acquire(self.target, wait=False)
            with self.assertRaises(DataFactoryError):
                Governor.acquire(self.target, wait=False)
        for permit in [*permits, cleanup]:
            Governor.release(permit)

    def test_reserved_cleanup_capacity_cannot_be_given_to_aged_normal_waiter(self):
        from src.apps.data_factory.schemas.performance import DatasourceGovernorState, DatasourceWaiter
        group = Governor.target_policy(self.target, self.policy)[2]
        state = DatasourceGovernorState(tokens=20, normal_tokens=15, updated_at=self.store.now,
            waiters={'old': DatasourceWaiter(lane='normal', created_at=self.store.now-10, expires_at=self.store.now+30)})
        self.store.values[f'group:{group}:control'] = state.model_dump(mode='json')
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            permit = Governor.acquire(self.target, wait=False)
        self.assertIsNotNone(permit)
        Governor.release(permit)
        self.assertIn('old', self.store.values[f'group:{group}:control']['waiters'])

    def test_local_probe_queue_does_not_mix_cleanup_and_normal_lanes(self):
        from src.apps.data_factory.services.datasource_wait import DatasourceAdmissionProbeService as Probe
        group = Governor.target_policy(self.target, self.policy)[2]
        normal_key = (group, 'operation', 'normal')
        with patch.object(Probe, '_due', {}), patch.object(Probe, '_pid', __import__('os').getpid()):
            Probe.congested(normal_key, 'normal_head', self.store.now - 10)
            with patch.object(Probe, 'delay', wraps=Probe.delay) as delay, \
                    patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
                permit = Governor.acquire(self.target)
            self.assertEqual(delay.call_args.args[0], (group, 'operation', 'cleanup'))
            Governor.release(permit)

    def test_hundred_cases_create_verify_cleanup_with_bounded_connections_and_zero_residue(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        from sqlalchemy import create_engine, text
        from src.apps.data_factory.services.datasource_pool import DatasourceQueuePool
        from src.apps.data_factory.services.datasource_connection import GovernedDbapiConnection
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService as Waiting
        from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService as Audit
        from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor, cooperative_sleep

        # 本地物理 SQL + 真实配额算法；仅控制库存储换成原子内存桩，不访问业务库。
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'regression.sqlite'
            engine = create_engine('sqlite://', poolclass=DatasourceQueuePool, pool_size=2, max_overflow=0,
                pool_timeout=0, isolation_level='AUTOCOMMIT', creator=lambda: GovernedDbapiConnection.connect(self.target,
                    lambda: sqlite3.connect(path, check_same_thread=False, timeout=5)))
            self.addCleanup(engine.dispose)
            with engine.begin() as connection:
                connection.execute(text('CREATE TABLE fixture (id INTEGER PRIMARY KEY, value TEXT NOT NULL)'))
            executor = CooperativeCaseExecutor(10, 'datasource-100-case')
            self.addCleanup(executor.shutdown)
            lock = threading.Lock()
            active = peak = connection_peak = 0
            waits = []
            started = time.monotonic()

            def lane():
                return (DatasourceQueueLaneEnum.CLEANUP if Audit.current_source().get('source_stage') == 'cleanup'
                        else DatasourceQueueLaneEnum.NORMAL)

            def operation(connection, sql, parameters):
                nonlocal active, peak, connection_peak
                with Governor.operation(self.target, physical=True):
                    with lock:
                        active += 1
                        peak = max(peak, active)
                        state = next(iter(self.store.values.values()))
                        connection_peak = max(connection_peak, sum(value['slots'] for value in state['permits'].values()
                                                                  if value['kind'] == 'connection'))
                    try:
                        return connection.execute(text(sql), parameters)
                    finally:
                        with lock:
                            active -= 1

            def case(index):
                with Waiting.owner(None):
                    try:
                        with engine.begin() as connection:
                            operation(connection, 'INSERT INTO fixture VALUES (:id, :value)',
                                      {'id': index, 'value': f'AUTO_{index}'})
                        self.assertTrue(connection.closed)
                        # 此处模拟业务接口阶段，必须不持有数据库连接或操作名额。
                        cooperative_sleep(0.002)
                        if index % 9 == 0:
                            raise RuntimeError('AUTO_CONTROLLED_BUSINESS_FAILURE')
                        with engine.connect() as connection:
                            self.assertEqual(operation(connection, 'SELECT value FROM fixture WHERE id=:id',
                                                       {'id': index}).scalar_one(), f'AUTO_{index}')
                    except RuntimeError as error:
                        if str(error) != 'AUTO_CONTROLLED_BUSINESS_FAILURE':
                            raise
                    finally:
                        with Audit.source({'source_stage': 'cleanup'}):
                            with engine.begin() as connection:
                                operation(connection, 'DELETE FROM fixture WHERE id=:id', {'id': index})
                                self.assertEqual(operation(connection, 'SELECT COUNT(*) FROM fixture WHERE id=:id',
                                                           {'id': index}).scalar_one(), 0)
                        with lock:
                            waits.append(Waiting.elapsed())

            # 加速令牌时间，不提高并发/连接预算；同一逻辑秒不因等待者数量重复累加。
            original_change = Governor.change
            clock_base = self.store.now
            def change(*args, **kwargs):
                with lock:
                    self.store.now = clock_base + (time.monotonic() - started) * 50
                return original_change(*args, **kwargs)

            with patch.object(Governor, 'lane', side_effect=lane), \
                    patch.object(Governor, 'change', side_effect=change), \
                    patch.object(Governor, 'relieve_connection_pressure'), \
                    patch('django.db.connections.all', return_value=[]):
                futures = [executor.submit(case, index) for index in range(1, 101)]
                for future in futures:
                    future.result(timeout=30)
            executor.shutdown()
            with engine.connect() as connection:
                self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM fixture')).scalar_one(), 0)
            self.assertEqual(engine.pool.checkedout(), 0)
            engine.dispose()
            state = next(iter(self.store.values.values()))
            self.assertFalse(state['permits'])
            self.assertFalse(state['waiters'])
            self.assertLessEqual(peak, self.policy.mysql.concurrency)
            self.assertLessEqual(connection_peak, self.policy.mysql.connections)
            self.assertEqual(len(waits), 100)
            import logging
            ordered = sorted(waits)
            logging.getLogger(__name__).info(
                'event=datasource_local_regression cases=100 elapsed=%.3f wait_p95=%.3f wait_p99=%.3f '
                'wait_max=%.3f operations_peak=%s connections_peak=%s residue=0',
                time.monotonic() - started, ordered[94], ordered[98], ordered[-1], peak, connection_peak)

    def test_full_expanded_wait_queue_keeps_waiting_without_sending_or_discarding_registered_requests(self):
        from src.apps.data_factory.schemas.performance import DatasourceGovernorState, DatasourceWaiter
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        self.policy.max_waiters = DatasourcePerformancePolicy().max_waiters
        group = Governor.target_policy(self.target, self.policy)[2]
        state = DatasourceGovernorState(waiters={f'{i:032x}': DatasourceWaiter(
            lane='normal', created_at=self.store.now - 1, expires_at=self.store.now + 30)
            for i in range(self.policy.max_waiters)})
        key = f'group:{group}:control'
        self.store.values[key] = state.model_dump(mode='json')
        with patch.object(DatasourceWaitService, 'pause', side_effect=RuntimeError('AUTO_STOP_WAIT')):
            with self.assertRaisesRegex(RuntimeError, 'AUTO_STOP_WAIT'):
                Governor.acquire(self.target)
        self.assertEqual(len(self.store.values[key]['waiters']), 256)
        self.assertFalse(self.store.values[key]['permits'])

    def test_new_defaults_keep_shared_hard_limits_and_two_cleanup_slots_across_threads(self):
        defaults = DatasourcePerformancePolicy()
        self.policy.mysql = defaults.mysql
        self.policy.pool_size = defaults.pool_size
        pools = [Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION,
                                  cost=defaults.pool_size, wait=False) for _ in range(3)]
        with self.assertRaises(DataFactoryError):
            Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION,
                             cost=defaults.pool_size, wait=False)
        def claim(_):
            try:
                return Governor.acquire(self.target, wait=False)
            except DataFactoryError:
                return None
        with ThreadPoolExecutor(max_workers=16) as executor:
            operations = [permit for permit in executor.map(claim, range(16)) if permit]
        self.assertEqual(len(operations), 4)
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            pools.append(Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION,
                                          cost=defaults.pool_size, wait=False))
            operations.extend(Governor.acquire(self.target, wait=False) for _ in range(2))
            with self.assertRaises(DataFactoryError):
                Governor.acquire(self.target, wait=False)
        state = next(iter(self.store.values.values()))
        self.assertEqual(sum(value['slots'] for value in state['permits'].values() if value['kind'] == 'connection'), 12)
        self.assertEqual(sum(value['kind'] == 'operation' for value in state['permits'].values()), 6)
        for permit in operations + pools:
            Governor.release(permit)
        self.assertFalse(next(iter(self.store.values.values()))['permits'])

    def test_thirty_cases_queue_without_replay_or_exceeding_instance_limits(self):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        barrier = threading.Barrier(30)
        lock = threading.Lock()
        active = peak = connection_peak = 0
        writes = []
        clock_start, clock_base = time.monotonic(), self.store.now

        def pause(seconds=0.1):
            with lock:
                # 多个等待者共享时钟，不能将同一段等待重复累加 30 次。
                self.store.now = clock_base + (time.monotonic() - clock_start) * 20
            time.sleep(0.005)

        def case(index):
            nonlocal active, peak, connection_peak
            barrier.wait(timeout=5)
            connection = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION)
            try:
                with lock:
                    state = next(iter(self.store.values.values()))
                    connection_peak = max(connection_peak, sum(value['slots'] for value in state['permits'].values()
                                                              if value['kind'] == 'connection'))
                with Governor.operation(self.target, physical=True):
                    with lock:
                        active += 1
                        peak = max(peak, active)
                        writes.append(index)
                    time.sleep(0.005)
                    with lock:
                        active -= 1
            finally:
                Governor.connection_closed(connection)

        with patch.object(DatasourceWaitService, 'pause', side_effect=pause), \
                patch.object(Governor, 'relieve_connection_pressure'), \
                ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(case, index) for index in range(30)]
            for future in futures:
                future.result(timeout=15)
        self.assertEqual(sorted(writes), list(range(30)))
        self.assertLessEqual(peak, 3)
        self.assertLessEqual(connection_peak, 6)
        state = next(iter(self.store.values.values()))
        self.assertFalse(state['permits'])
        self.assertFalse(state['waiters'])

    def test_normal_contention_beyond_old_deadline_still_waits_and_renews_fifo_position(self):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        permits = [Governor.acquire(self.target, wait=False) for _ in range(3)]
        owners = []
        def pause(seconds):
            state = next(iter(self.store.values.values()))
            owners.append(next(iter(state['waiters'])))
            self.store.now += 10
            if len(owners) == 5:
                Governor.release(permits.pop())
        with patch.object(DatasourceWaitService, 'pause', side_effect=pause), \
                patch('src.apps.data_factory.services.datasource_governor.time.monotonic',
                      side_effect=lambda: self.store.now):
            fresh = Governor.acquire(self.target)
        self.assertEqual(len(owners), 5)
        self.assertEqual(len(set(owners)), 1)
        for permit in [fresh, *permits]:
            Governor.release(permit)

    def test_protocol_pool_reservation_is_atomic_and_counts_physical_slots(self):
        permits = [Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, cost=2, wait=False)
                   for _ in range(3)]
        with self.assertRaises(DataFactoryError):
            Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, cost=2, wait=False)
        state = next(iter(self.store.values.values()))
        self.assertEqual(sum(value['slots'] for value in state['permits'].values()), 6)
        self.assertEqual(len(state['permits']), 3)
        for permit in permits:
            Governor.connection_closed(permit)

    def test_same_instance_different_connection_accounts_share_budget(self):
        another = SimpleNamespace(id=99, db_type=0, host='MYSQL.EXAMPLE.COM.', port=3306, user='other')
        self.assertEqual(Governor.target_policy(self.target)[2], Governor.target_policy(another)[2])
        self.assertNotEqual(Governor.target_policy(self.target)[2], Governor.target_policy(
            SimpleNamespace(id=99, db_type=0, host='other.example.com', port=3306))[2])

    def test_expired_and_unknown_permits_are_not_silently_released(self):
        permits = [Governor.acquire(self.target, wait=False) for _ in range(3)]
        Governor.release(permits[0], unknown=True)
        self.store.now += 1000
        with self.assertRaises(DataFactoryError):
            Governor.acquire(self.target, wait=False)
        state = next(iter(self.store.values.values()))
        self.assertEqual(len(state['permits']), 3)
        self.assertTrue(all(item['state'] == 'suspect' for item in state['permits'].values()))

    def test_connection_quota_includes_idle_connection_reservations(self):
        permits = [Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
                   for _ in range(6)]
        with self.assertRaises(DataFactoryError):
            Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        Governor.release(permits[0])
        Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            for _ in range(2):
                Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
            with self.assertRaises(DataFactoryError):
                Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)

    def test_control_plane_failure_blocks_operation(self):
        with patch.object(self.store, 'atomic_update', side_effect=OSError('unavailable')):
            with self.assertRaises(DataFactoryError) as error:
                Governor.acquire(self.target, wait=False)
        self.assertEqual(error.exception.code, 34185)

    def test_healthy_concurrency_saturation_is_still_busy_not_reconciliation(self):
        for _ in range(3):
            Governor.acquire(self.target, wait=False)
        with self.assertRaises(DataFactoryError) as caught:
            Governor.acquire(self.target, wait=False)
        self.assertEqual(caught.exception.code, 34186)

    def test_eight_unknown_connections_are_reported_without_releasing_or_executing(self):
        permits = [Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
                   for _ in range(6)]
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            permits.extend(Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
                           for _ in range(2))
        self.store.now += 1000
        with self.assertRaises(DataFactoryError) as caught:
            Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        self.assertEqual(caught.exception.code, 34191)
        self.assertTrue(caught.exception._datasource_not_sent)
        state = next(iter(self.store.values.values()))
        self.assertEqual(len(state['permits']), 8)
        self.assertTrue(all(value['state'] == 'suspect' for value in state['permits'].values()))
        self.assertFalse(Governor._pending_releases)

    def test_unrelated_suspect_does_not_misclassify_live_operation_saturation(self):
        connection = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        Governor.release(connection, unknown=True)
        for _ in range(3):
            Governor.acquire(self.target, wait=False)
        with self.assertRaises(DataFactoryError) as caught:
            Governor.acquire(self.target, wait=False)
        self.assertEqual(caught.exception.code, 34186)

    def test_instance_blocked_by_unknown_operations_is_reconciliation_required(self):
        operations = [Governor.acquire(self.target, wait=False) for _ in range(3)]
        for operation in operations:
            Governor.release(operation, unknown=True)
        with self.assertRaises(DataFactoryError) as caught:
            Governor.acquire(self.target, wait=False)
        self.assertEqual(caught.exception.code, 34191)

    def test_connection_heartbeat_extends_only_unexpired_known_ownership(self):
        first = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        second = Governor.acquire(self.target, kind=DatasourcePermitKindEnum.CONNECTION, wait=False)
        self.store.now += 15
        Governor.release(first, unknown=True)
        Governor.renew_connections([first, second])
        state = next(iter(self.store.values.values()))
        self.assertEqual(state['permits'][first[1]]['state'], 'suspect')
        self.assertEqual(state['permits'][second[1]]['expires_at'], self.store.now + 300)
        self.store.now += 1000
        Governor.renew_connections([second])
        state = next(iter(self.store.values.values()))
        self.assertEqual(state['permits'][second[1]]['state'], 'suspect')

    def test_accounts_products_and_environments_share_instance_budget(self):
        first = Governor.acquire(self.target, wait=False)
        self.target = SimpleNamespace(**{**vars(self.target), 'id': 2, 'user': 'other', 'project_product_id': 8, 'test_env': 0})
        Governor.acquire(self.target, wait=False)
        Governor.acquire(self.target, wait=False)
        with self.assertRaises(DataFactoryError) as caught:
            Governor.acquire(self.target, wait=False)
        self.assertEqual(caught.exception.code, 34186)
        with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
            Governor.acquire(self.target, wait=False)
        self.assertEqual(len(next(iter(self.store.values.values()))['permits']), 4)
        Governor.release(first)

    def test_lowering_budget_does_not_drop_existing_permits(self):
        for _ in range(3):
            Governor.acquire(self.target, wait=False)
        self.policy.mysql.concurrency = 2
        with self.assertRaises(DataFactoryError):
            Governor.acquire(self.target, wait=False)
        self.assertEqual(len(next(iter(self.store.values.values()))['permits']), 3)

    def test_owner_cannot_release_someone_elses_permit(self):
        permit = Governor.acquire(self.target, wait=False)
        Governor.release((permit[0], 'unrelated-owner'))
        self.assertIn(permit[1], next(iter(self.store.values.values()))['permits'])

    def test_redis_cost_gate_does_not_rewrite_unsafe_commands(self):
        for parts in (['SELECT', '1'], ['AUTH', 'password'], ['SUBSCRIBE', 'topic'], ['KEYS', '*']):
            with self.subTest(command=parts[0]), self.assertRaises(DataFactoryError):
                DatasourceCostService.redis(parts)
        DatasourceCostService.redis(['SCAN', '0', 'MATCH', 'AUTO_*', 'COUNT', '100'])
        DatasourceCostService.redis(['HGET', 'AUTO_key', 'name'])
        for parts in (['SMEMBERS', 'key'], ['HGETALL', 'key'], ['LRANGE', 'key', '0', '-1'], ['SCAN', '0']):
            DatasourceCostService.redis(parts)

    def test_es_cost_gate_does_not_reject_by_dsl_shape(self):
        for index, query in [('', {}), ('example', {'size': -1}), ('example', {'from': 'invalid'})]:
            with self.subTest(index=index), self.assertRaises(DataFactoryError):
                DatasourceCostService.elasticsearch(index, query)
        DatasourceCostService.elasticsearch('example', {'size': 1, 'query': {'term': {'id': 'AUTO_example'}}})
        for index, query in [('*', {}), ('example', {'query': {'term': {'script': 'AUTO_value'}}}),
                             ('example', {'from': 9999, 'size': 2})]:
            DatasourceCostService.elasticsearch(index, query)

    def test_sql_session_and_intentional_blocking_cannot_pollute_shared_pool(self):
        for sql in ('SET @tenant=7', 'SELECT @tenant:=7', 'SELECT GET_LOCK(\'name\',30)',
                    'SELECT SLEEP(60)', 'CREATE\nTEMPORARY TABLE demo(id int)', 'SELECT 1; SELECT 2'):
            with self.subTest(sql=sql), self.assertRaises(DataFactoryError):
                DatasourceCostService.sql(sql)
        DatasourceCostService.sql("SELECT 'user@example.com', 'SLEEP(60)' AS name")

    def test_unknown_write_results_are_not_confused_with_rejected_connections(self):
        from urllib.error import HTTPError
        from pymysql.err import OperationalError
        for error in (OperationalError(2013, 'lost response'), TimeoutError('response timeout'),
                      HTTPError('https://example.com', 503, 'unavailable', {}, None)):
            self.assertTrue(Governor.outcome_unknown(error))
        for error in (OperationalError(2003, 'connect refused'), ConnectionRefusedError(),
                      HTTPError('https://example.com', 403, 'forbidden', {}, None)):
            self.assertFalse(Governor.outcome_unknown(error))

    def test_nested_admission_keeps_parent_performance_source_for_sql_audit(self):
        from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService as Audit
        with Governor.operation(self.target, physical=True) as admitted:
            self.assertEqual(Audit.current_source()['performance'], admitted)
            with Governor.operation(self.target) as nested:
                self.assertIsNone(nested)
                self.assertEqual(Audit.current_source()['performance'], admitted)
        self.assertNotIn('performance', Audit.current_source())

    def test_oversized_sql_result_fails_without_silent_assertion_truncation(self):
        connection, result = Mock(), Mock()
        with self.assertRaises(DataFactoryError) as caught:
            DatasourceCostService.abort_result(connection, result, limit=100, observed_rows=101)
        connection.invalidate.assert_called_once_with()
        result.close.assert_called_once_with()
        self.assertFalse(Governor.outcome_unknown(caught.exception))
        self.assertEqual(caught.exception.code, 34194)
        self.assertIn('100 行', caught.exception.msg)
        self.assertIn('至少 101 行', caught.exception.msg)
        self.assertIn('请检查用例 SQL 是否未限制查询条数或查询范围过大，并及时修改用例', caught.exception.msg)

    def test_oversized_write_result_or_unconfirmed_close_still_requires_reconciliation(self):
        for is_write, close_error in ((True, None), (False, OSError('AUTO close unconfirmed'))):
            connection, result = Mock(), Mock()
            connection.invalidate.side_effect = close_error
            with self.assertRaises(DataFactoryError) as caught:
                DatasourceCostService.abort_result(connection, result, limit=100, observed_rows=101, is_write=is_write)
            self.assertTrue(Governor.outcome_unknown(caught.exception))
            result.close.assert_called_once_with()
