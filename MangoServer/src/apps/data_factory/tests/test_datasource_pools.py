import os
import threading
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.datasource_pool import DatasourcePoolRegistry as SqlPools
from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry as ProtocolPools
from src.apps.data_factory.services.redis_protocol import BoundedRedisBuffer
from src.apps.data_factory.exceptions import DataFactoryError


class DatasourcePoolTests(SimpleTestCase):
    def setUp(self):
        self.policy = DatasourcePerformancePolicy()
        self.target = SimpleNamespace(id=1, db_type=0, update_time='version1', user='reader', host='example.com',
                                      port=9200, extra_config={}, cache_key='credential-key')
        for path, kwargs in [
            ('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.policy',
             {'return_value': self.policy}),
            ('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.acquire',
             {'side_effect': [('group', str(i)) for i in range(30)]}),
            ('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.release', {}),
            ('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.connections_closed', {}),
            ('src.apps.data_factory.services.protocol_pool.threading.Thread', {}),
        ]:
            guard = patch(path, **kwargs)
            guard.start()
            self.addCleanup(guard.stop)
        for registry, attr in ((SqlPools, '_engines'), (ProtocolPools, '_entries')):
            guard = patch.object(registry, attr, {})
            guard.start()
            self.addCleanup(guard.stop)
        SqlPools._pid = ProtocolPools._pid = os.getpid()
        SqlPools._reaper = ProtocolPools._thread = Mock()

    def test_engine_dispose_returns_reference_without_destroying_shared_pool(self):
        engine = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0))
        dispose = engine.dispose
        factory = Mock(return_value=engine)
        first = SqlPools.get_engine(self.target, 5, factory)
        second = SqlPools.get_engine(self.target, 5, factory)
        self.assertIs(first, second)
        first.dispose()
        dispose.assert_not_called()
        second.dispose()
        SqlPools.prune(0)
        dispose.assert_called_once()
        self.assertFalse(SqlPools._engines)

    def test_protocol_pool_reuses_credentials_but_not_different_versions(self):
        factory = Mock(side_effect=lambda size: Mock())
        with ProtocolPools.borrow(self.target, 'elasticsearch', factory) as first:
            pass
        with ProtocolPools.borrow(self.target, 'elasticsearch', factory) as same:
            self.assertIs(first, same)
        self.target.update_time = 'version2'
        with ProtocolPools.borrow(self.target, 'elasticsearch', factory) as updated:
            self.assertIsNot(first, updated)
        self.assertEqual(factory.call_count, 2)
        ProtocolPools.prune(0)
        self.assertTrue(first.close.called)
        self.assertTrue(updated.close.called)

    def test_protocol_transport_failure_discards_connection_pool(self):
        client = Mock()
        with self.assertRaises(TimeoutError):
            with ProtocolPools.borrow(self.target, 'redis', lambda size: client):
                raise TimeoutError()
        client.close.assert_called_once()
        self.assertFalse(ProtocolPools._entries)

    def test_sql_pressure_closes_idle_pool_but_never_checked_out_connections(self):
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0))
        busy = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 1))
        idle_close, busy_close = idle.dispose, busy.dispose
        SqlPools.get_engine(self.target, 5, lambda policy: idle)
        SqlPools.get_engine(self.target, 6, lambda policy: busy)
        idle_close.reset_mock()
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
        SqlPools.relieve_pressure(Governor.target_policy(self.target, self.policy)[2])
        idle_close.assert_called_once()
        busy_close.assert_not_called()

    def test_one_case_can_hold_multiple_engine_handles_without_waiting_for_itself(self):
        self.policy.max_local_pools = 1
        factory = lambda policy: SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0))
        first = SqlPools.get_engine(self.target, 5, factory)
        second = SqlPools.get_engine(self.target, 6, factory)
        self.assertIsNot(first, second)
        first.dispose()
        second.dispose()
        self.assertLessEqual(len(SqlPools._engines), self.policy.max_local_pools)
        SqlPools.prune(0)
        self.assertFalse(SqlPools._engines)

    def test_protocol_cache_wait_does_not_hold_lock_needed_to_return_client(self):
        self.policy.max_local_pools = 1
        another = SimpleNamespace(**vars(self.target))
        another.id = 2
        started, finished = threading.Event(), threading.Event()
        failures = []
        def borrow_second():
            started.set()
            try:
                with ProtocolPools.borrow(another, 'redis', lambda size: Mock()):
                    pass
            except BaseException as error:
                failures.append(error)
            finally:
                finished.set()
        with ProtocolPools.borrow(self.target, 'redis', lambda size: Mock()):
            thread = Thread(target=borrow_second, daemon=True)
            thread.start()
            self.assertTrue(started.wait(1))
            self.assertFalse(finished.wait(0.05))
        self.assertTrue(finished.wait(2))
        thread.join(timeout=1)
        self.assertFalse(failures)
        ProtocolPools.prune(0)

    def test_protocol_borrow_waits_before_client_pool_can_timeout(self):
        self.policy.pool_size = 1
        factory = Mock(return_value=Mock())
        started, borrowed = threading.Event(), threading.Event()
        failures = []
        def borrow_second():
            started.set()
            try:
                with ProtocolPools.borrow(self.target, 'elasticsearch', factory):
                    borrowed.set()
            except BaseException as error:
                failures.append(error)
        with ProtocolPools.borrow(self.target, 'elasticsearch', factory):
            thread = Thread(target=borrow_second, daemon=True)
            thread.start()
            self.assertTrue(started.wait(1))
            self.assertFalse(borrowed.wait(0.05))
        self.assertTrue(borrowed.wait(2))
        thread.join(timeout=1)
        self.assertFalse(failures)
        factory.assert_called_once_with(1)
        ProtocolPools.prune(0)

    @patch('src.apps.data_factory.services.redis_protocol.SystemConfigService.get_ranged_int', return_value=200)
    def test_redis_declared_large_payload_is_rejected_before_allocation(self, limit):
        raw = Mock()
        raw.readline.return_value = b'$900000000'
        buffer = BoundedRedisBuffer(raw)
        with self.assertRaises(DataFactoryError):
            buffer.readline()
        raw.read.assert_not_called()

    def test_expired_protocol_pool_is_fenced_until_borrower_finishes_then_physically_closed(self):
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
        client = Mock()
        with ProtocolPools.borrow(self.target, 'redis', lambda size: client):
            entry = next(iter(ProtocolPools._entries.values()))
            with patch.object(Governor, 'renew_connections', return_value=set(entry['permits'])):
                ProtocolPools.renew_live_connections()
            self.assertTrue(entry['broken'])
            client.close.assert_not_called()
        client.close.assert_called_once()
        self.assertFalse(ProtocolPools._entries)

    def test_expired_sql_idle_pool_is_closed_but_checked_out_work_is_not_interrupted(self):
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0))
        busy = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 1))
        idle_close, busy_close = idle.dispose, busy.dispose
        SqlPools.get_engine(self.target, 5, lambda policy: idle)
        SqlPools.get_engine(self.target, 6, lambda policy: busy)
        idle_close.reset_mock()
        group = Governor.target_policy(self.target, self.policy)[2]
        with patch.object(Governor, 'renew_connections', return_value={(group, 'expired-owner')}):
            SqlPools.renew_live_connections()
        idle_close.assert_called_once()
        busy_close.assert_not_called()

    def test_graceful_shutdown_closes_idle_sql_and_protocol_pools(self):
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0))
        close = idle.dispose
        engine = SqlPools.get_engine(self.target, 5, lambda policy: idle)
        engine.dispose()
        client = Mock()
        with ProtocolPools.borrow(self.target, 'elasticsearch', lambda size: client):
            pass
        SqlPools.close_all()
        ProtocolPools.close_all()
        close.assert_called_once()
        client.close.assert_called_once()
