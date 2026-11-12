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
from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor


class AtomicMemoryStore:
    def __init__(self):
        self.values = {}
        self.now = 1_800_000_000
        self.lock = threading.RLock()
        self.using = 'unit'
        self.name = 'datasource_governor'
        self.policy = {'max_bytes': 131072}

    def control_connection(self):
        return nullcontext()

    def get(self, key, default=None):
        return copy.deepcopy(self.values.get(key, default))

    def set(self, key, value, ttl=None):
        self.values[key] = copy.deepcopy(value)

    def set_if_absent(self, key, value, ttl=None):
        if key not in self.values:
            self.set(key, value)

    def delete(self, key):
        self.values.pop(key, None)

    def atomic_update(self, key, transform, ttl=None, utc_clock=False):
        with self.lock:
            value, result = transform(copy.deepcopy(self.values.get(key)), datetime.fromtimestamp(self.now, timezone.utc))
            self.values[key] = copy.deepcopy(value)
            return result


class DatasourcePerformanceTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        self.policy = DatasourcePerformancePolicy(mysql=DatasourceTypeBudget(connections=8), pool_size=2)
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                      patch.object(Governor, 'policy', return_value=self.policy),
                      patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()),
                      patch.object(Governor, '_pending_releases', set()),
                      patch.object(Governor, '_closed_connections', set())):
            guard.start()
            self.addCleanup(guard.stop)

    def test_only_connections_are_limited_and_cleanup_connections_are_reserved(self):
        with Governor.nonblocking_admission():
            normal = [Governor.acquire(self.target) for _ in range(6)]
            with self.assertRaises(DataFactoryError):
                Governor.acquire(self.target)
            with patch.object(Governor, 'lane', return_value=DatasourceQueueLaneEnum.CLEANUP):
                cleanup = [Governor.acquire(self.target) for _ in range(2)]
                with self.assertRaises(DataFactoryError):
                    Governor.acquire(self.target)
        for permit in normal + cleanup:
            Governor.connection_closed(permit)
        self.assertFalse(self.store.values[f'group:{normal[0][0]}:control']['permits'])

    def test_old_operation_occupancy_does_not_block_new_connections(self):
        from src.apps.data_factory.schemas.performance import DatasourcePermit
        group = Governor.target_policy(self.target)[2]
        Governor.change(group, lambda state, now: state.permits.update({
            'historical': DatasourcePermit(owner='historical', process='old-worker', lane='normal',
                kind='operation', state='suspect', expires_at=now-1000, slots=128)}))
        permit = Governor.acquire(self.target)
        self.assertIn('historical', self.store.values[f'group:{group}:control']['permits'])
        Governor.connection_closed(permit)

    def test_full_connection_budget_waits_without_case_failure_or_deadline(self):
        with Governor.nonblocking_admission():
            held = [Governor.acquire(self.target) for _ in range(6)]
        def progress(*args, **kwargs):
            self.store.now += 3600
            Governor.connection_closed(held.pop())
        with patch.object(Governor, 'relieve_connection_pressure'), \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause', side_effect=progress):
            fresh = Governor.acquire(self.target)
        for permit in held + [fresh]:
            Governor.connection_closed(permit)

    def test_unknown_physical_occupancy_waits_until_other_connection_closes_without_case_failure(self):
        from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        held = [Governor.acquire(self.target) for _ in range(6)]
        group, owner = held[0]
        self.store.values[f'group:{group}:control']['permits'][owner]['state'] = 'suspect'
        callback = Mock()
        def progress(*args, **kwargs):
            callback.assert_not_called()
            self.assertEqual(self.store.values[f'group:{group}:control']['permits'][owner]['state'], 'suspect')
            Governor.connection_closed(held.pop())
        with Infrastructure.scope(), \
                patch.object(Governor, 'relieve_connection_pressure'), \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause',
                      side_effect=progress) as pause:
            connection = GovernedDbapiConnection.connect(self.target, callback)
            self.assertEqual(Infrastructure.current(), [])
        callback.assert_called_once()
        pause.assert_called_once()
        self.assertIn(owner, self.store.values[f'group:{group}:control']['permits'])
        connection.close()
        for permit in held:
            Governor.connection_closed(permit)

    def test_unknown_connections_remain_protected_for_nonblocking_recovery_probes(self):
        held = [Governor.acquire(self.target) for _ in range(6)]
        group, owner = held[0]
        self.store.values[f'group:{group}:control']['permits'][owner]['state'] = 'suspect'
        with Governor.nonblocking_admission(), self.assertRaises(DataFactoryError):
            Governor.acquire(self.target)
        self.assertEqual(len(self.store.values[f'group:{group}:control']['permits']), 6)
        for permit in held:
            Governor.connection_closed(permit)

    def test_100_operations_after_worker_rebuild_wait_without_replay_or_exceeding_budget(self):
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
        historical = [Governor.acquire(self.target) for _ in range(2)]
        group = historical[0][0]
        for _, owner in historical:
            self.store.values[f'group:{group}:control']['permits'][owner]['state'] = 'suspect'
        sent, peak = [], [0]
        deadline = time.monotonic() + 10

        def pause(*args, **kwargs):
            if time.monotonic() >= deadline:
                raise AssertionError('AUTO bounded test did not make progress')
            time.sleep(0.001)

        def operation(number):
            permit = None
            with Audit.source({'source_stage': 'cleanup' if number % 5 == 0 else 'query'}):
                try:
                    permit = Governor.acquire(self.target)
                    with self.store.lock:
                        values = self.store.values[f'group:{group}:control']['permits'].values()
                        used = sum(value['slots'] for value in values if value['kind'] == 'connection')
                        self.assertLessEqual(used, self.policy.mysql.connections)
                        peak[0] = max(peak[0], used)
                        sent.append(number)
                    time.sleep(0.002)
                finally:
                    if permit:
                        Governor.connection_closed(permit)

        with patch.object(Governor, 'process_identity', return_value='AUTO_NEW_WORKER'), \
                patch.object(Governor, 'relieve_connection_pressure'), \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause',
                      side_effect=pause), ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(operation, range(100)))
        self.assertEqual(sorted(sent), list(range(100)))
        self.assertLessEqual(peak[0], 8)
        self.assertEqual(set(self.store.values[f'group:{group}:control']['permits']),
                         {owner for _, owner in historical})
        self.assertTrue(all(value['state'] == 'suspect'
                            for value in self.store.values[f'group:{group}:control']['permits'].values()))
        for permit in historical:
            Governor.connection_closed(permit)

    def test_wait_interruption_never_sends_or_releases_an_unknown_connection(self):
        held = [Governor.acquire(self.target) for _ in range(6)]
        group, owner = held[0]
        self.store.values[f'group:{group}:control']['permits'][owner]['state'] = 'suspect'
        from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
        callback = Mock()
        with patch.object(Governor, 'relieve_connection_pressure'), \
                patch('src.apps.data_factory.services.governance.datasource_wait.DatasourceWaitService.pause',
                      side_effect=InterruptedError('AUTO stopped')):
            with self.assertRaises(InterruptedError):
                GovernedDbapiConnection.connect(self.target, callback)
        callback.assert_not_called()
        self.assertEqual(len(self.store.values[f'group:{group}:control']['permits']), 6)
        for permit in held:
            Governor.connection_closed(permit)

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
