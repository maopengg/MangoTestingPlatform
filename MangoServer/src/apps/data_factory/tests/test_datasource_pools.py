import os
import threading
from contextlib import contextmanager
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.pool.datasource_pool import DatasourcePoolRegistry as SqlPools
from src.apps.data_factory.services.pool.protocol_pool import ProtocolPoolRegistry as ProtocolPools
from src.apps.data_factory.services.protocols.redis_protocol import BoundedRedisBuffer
from src.apps.data_factory.exceptions import DataFactoryError


class DatasourcePoolTests(SimpleTestCase):
    def setUp(self):
        self.policy = DatasourcePerformancePolicy()
        self.target = SimpleNamespace(id=1, db_type=0, update_time='version1', user='reader', host='example.com',
                                      port=9200, extra_config={}, cache_key='credential-key')
        for path, kwargs in [
            ('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
             {'return_value': self.policy}),
            ('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.acquire',
             {'side_effect': [('group', str(i)) for i in range(30)]}),
            ('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.release', {}),
            ('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.connections_closed', {}),
            ('src.apps.data_factory.services.pool.protocol_pool.threading.Thread', {}),
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
        engine = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
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

    def test_sql_slow_lease_renewal_does_not_block_shared_engine_borrowers(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        entered, finish = threading.Event(), threading.Event()
        engine = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
        SqlPools.get_engine(self.target, 5, lambda policy: engine).dispose()

        def renew(permits):
            entered.set()
            if not finish.wait(3):
                raise AssertionError('renewal was never released')
            return set()

        def borrow(_):
            value = SqlPools.get_engine(self.target, 5, lambda policy: self.fail('shared pool rebuilt'))
            value.dispose()
            return value is engine

        outcomes = []
        with patch.object(Governor, 'renew_connections', side_effect=renew):
            renewal = Thread(target=SqlPools.renew_live_connections)
            renewal.start()
            try:
                self.assertTrue(entered.wait(1))
                jobs = [Thread(target=lambda: outcomes.extend(borrow(index) for index in range(25)))
                        for _ in range(4)]
                for job in jobs:
                    job.start()
                for job in jobs:
                    job.join(timeout=1)
                    self.assertFalse(job.is_alive())
                self.assertEqual(outcomes, [True] * 100)
                self.assertTrue(renewal.is_alive())
            finally:
                finish.set()
                renewal.join(timeout=1)
        self.assertEqual(next(iter(SqlPools._engines.values()))[3], 0)

    def test_protocol_slow_lease_renewal_does_not_block_borrow_or_return(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        entered, finish = threading.Event(), threading.Event()
        client = Mock()

        def renew(permits):
            entered.set()
            if not finish.wait(3):
                raise AssertionError('renewal was never released')
            return set()

        with ProtocolPools.borrow(self.target, 'redis', lambda size: client):
            with patch.object(Governor, 'renew_connections', side_effect=renew):
                renewal = Thread(target=ProtocolPools.renew_live_connections)
                renewal.start()
                try:
                    self.assertTrue(entered.wait(1))
                    with ProtocolPools.borrow(self.target, 'redis', lambda size: self.fail('pool rebuilt')) as value:
                        self.assertIs(value, client)
                    self.assertTrue(renewal.is_alive())
                finally:
                    finish.set()
                    renewal.join(timeout=1)
        self.assertEqual(next(iter(ProtocolPools._entries.values()))['active'], 0)

    def test_reaper_control_settlement_never_holds_registry_lock(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        for registry in (SqlPools, ProtocolPools):
            with self.subTest(registry=registry.__name__):
                entered, finish, available = threading.Event(), threading.Event(), threading.Event()
                failures = []

                def flush():
                    entered.set()
                    finish.wait(3)
                    registry._pid = -1

                def probe():
                    try:
                        with registry._lock:
                            available.set()
                    except BaseException as error:
                        failures.append(error)

                with patch('src.apps.data_factory.services.pool.datasource_pool.time.sleep'), \
                        patch.object(Governor, 'flush_pending_releases', side_effect=flush), \
                        patch.object(Governor, 'flush_closed_connections'), \
                        patch.object(Governor, 'connection_pressure', return_value=False), \
                        patch.object(registry, 'renew_live_connections'):
                    worker = Thread(target=registry.reap)
                    borrower = None
                    worker.start()
                    try:
                        self.assertTrue(entered.wait(1))
                        borrower = Thread(target=probe)
                        borrower.start()
                        self.assertTrue(available.wait(1))
                    finally:
                        finish.set()
                        worker.join(timeout=1)
                        if borrower is not None:
                            borrower.join(timeout=1)
                        registry._pid = os.getpid()
                self.assertFalse(failures)

    def test_slow_sql_pool_close_does_not_block_concurrent_new_pool_borrow(self):
        entered, finish, borrowed = threading.Event(), threading.Event(), threading.Event()
        failures = []
        def slow_close():
            entered.set()
            if not finish.wait(3):
                raise AssertionError('AUTO_CLOSE_NOT_RELEASED')
        original = SimpleNamespace(dispose=Mock(side_effect=slow_close),
                                   pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
        engine = SqlPools.get_engine(self.target, 5, lambda policy: original)
        engine.dispose()
        worker = Thread(target=lambda: SqlPools.prune(0))
        def borrow():
            try:
                fresh = SqlPools.get_engine(self.target, 5, lambda policy: SimpleNamespace(
                    dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock())))
                self.assertIsNot(fresh, original)
                fresh.dispose()
                borrowed.set()
            except BaseException as error:
                failures.append(error)
        borrower = None
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            borrower = Thread(target=borrow)
            borrower.start()
            self.assertTrue(borrowed.wait(1))
            self.assertTrue(worker.is_alive())
        finally:
            finish.set()
            worker.join(3)
            if borrower:
                borrower.join(3)
        self.assertFalse(failures)

    def test_late_old_engine_return_cannot_decrement_new_engine_borrowers(self):
        factory = lambda policy: SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(
            checkedout=lambda: 0, dispose=Mock()))
        old = SqlPools.get_engine(self.target, 5, factory)
        old.dispose()
        SqlPools.prune(0)
        fresh = SqlPools.get_engine(self.target, 5, factory)
        self.assertIsNot(old, fresh)
        old.dispose()
        self.assertEqual(next(iter(SqlPools._engines.values()))[3], 1)
        fresh.dispose()
        self.assertEqual(next(iter(SqlPools._engines.values()))[3], 0)

    def test_real_sql_engine_swaps_pool_before_slow_retired_pool_disposal(self):
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import QueuePool
        engine = create_engine('sqlite://', poolclass=QueuePool, connect_args={'check_same_thread': False})
        native_dispose = engine.dispose
        self.addCleanup(native_dispose)
        cached = SqlPools.get_engine(self.target, 5, lambda policy: engine)
        with cached.connect() as connection:
            self.assertEqual(connection.execute(text('select 1')).scalar_one(), 1)
        previous = engine.pool
        close = previous.dispose
        entered, finish = threading.Event(), threading.Event()
        def slow_close():
            entered.set()
            if not finish.wait(3):
                raise AssertionError('AUTO_CLOSE_NOT_RELEASED')
            close()
        with patch.object(previous, 'dispose', side_effect=slow_close):
            worker = Thread(target=lambda: SqlPools.relieve_pressure(engine._mango_instance_group))
            worker.start()
            try:
                self.assertTrue(entered.wait(1))
                self.assertIsNot(engine.pool, previous)
                self.assertIs(SqlPools.get_engine(self.target, 5, lambda policy: self.fail('rebuilt')), engine)
                with engine.connect() as connection:
                    self.assertEqual(connection.execute(text('select 2')).scalar_one(), 2)
                self.assertTrue(worker.is_alive())
            finally:
                finish.set()
                worker.join(3)

    def test_slow_protocol_close_and_settlement_do_not_block_another_borrow(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        for slow_phase in ('close', 'settlement'):
            with self.subTest(phase=slow_phase):
                ProtocolPools.close_all()
                entered, finish, borrowed = threading.Event(), threading.Event(), threading.Event()
                old, fresh = Mock(), Mock()
                def slow(*args):
                    entered.set()
                    if not finish.wait(3):
                        raise AssertionError('AUTO_CLOSE_NOT_RELEASED')
                with ProtocolPools.borrow(self.target, 'redis', lambda size: old):
                    pass
                guard = (patch.object(old, 'close', side_effect=slow) if slow_phase == 'close'
                         else patch.object(Governor, 'connections_closed', side_effect=slow))
                failures = []
                def borrow():
                    try:
                        with ProtocolPools.borrow(self.target, 'redis', lambda size: fresh) as current:
                            self.assertIs(current, fresh)
                            borrowed.set()
                    except BaseException as error:
                        failures.append(error)
                with guard:
                    worker = Thread(target=lambda: ProtocolPools.prune(0))
                    borrower = None
                    worker.start()
                    try:
                        self.assertTrue(entered.wait(1))
                        borrower = Thread(target=borrow)
                        borrower.start()
                        self.assertTrue(borrowed.wait(1))
                        self.assertTrue(worker.is_alive())
                    finally:
                        finish.set()
                        worker.join(3)
                        if borrower:
                            borrower.join(3)
                self.assertFalse(failures)

    def test_protocol_pressure_retires_only_idle_entries_in_the_requested_group(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        client = Mock()
        with ProtocolPools.borrow(self.target, 'redis', lambda size: client):
            pass
        group = Governor.target_policy(self.target, self.policy)[2]
        ProtocolPools.relieve_pressure('another-instance-group')
        client.close.assert_not_called()
        ProtocolPools.relieve_pressure(group)
        client.close.assert_called_once()

    def test_idle_protocol_maintenance_issue_does_not_pollute_the_current_case(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        from src.apps.data_factory.exceptions import DATASOURCE_SETTLEMENT_FAILED
        def settlement(*args):
            Infrastructure.capture(DataFactoryError(DATASOURCE_SETTLEMENT_FAILED))
        client = Mock()
        with ProtocolPools.borrow(self.target, 'redis', lambda size: client):
            pass
        with Infrastructure.scope(), patch.object(Governor, 'connections_closed', side_effect=settlement):
            ProtocolPools.prune(0)
            self.assertFalse(Infrastructure.current())

    def test_protocol_borrow_does_not_request_operation_quota(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        with patch.object(Governor, 'acquire', return_value=('group', 'owner')) as acquire:
            with ProtocolPools.borrow(self.target, 'redis', lambda size: Mock()):
                self.assertEqual(sum(entry['active'] for entry in ProtocolPools._entries.values()), 1)
            acquire.assert_called_once()
            self.assertEqual(acquire.call_args.kwargs, {'cost': self.policy.pool_size})

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
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
        busy = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 1, dispose=Mock()))
        idle_close, busy_close = idle.dispose, busy.dispose
        SqlPools.get_engine(self.target, 5, lambda policy: idle)
        SqlPools.get_engine(self.target, 6, lambda policy: busy)
        idle_close.reset_mock()
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        SqlPools.relieve_pressure(Governor.target_policy(self.target, self.policy)[2])
        idle_close.assert_called_once()
        busy_close.assert_not_called()

    def test_one_case_can_hold_multiple_engine_handles_without_waiting_for_itself(self):
        self.policy.max_local_pools = 1
        factory = lambda policy: SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
        first = SqlPools.get_engine(self.target, 5, factory)
        second = SqlPools.get_engine(self.target, 6, factory)
        self.assertIsNot(first, second)
        first.dispose()
        second.dispose()
        self.assertLessEqual(len(SqlPools._engines), self.policy.max_local_pools)
        SqlPools.prune(0)
        self.assertFalse(SqlPools._engines)

    def test_idle_pool_cache_limit_does_not_block_another_active_datasource(self):
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
            self.assertTrue(finished.wait(1))
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

    @patch('src.apps.data_factory.services.protocols.redis_protocol.SystemConfigService.get_ranged_int', return_value=200)
    def test_redis_declared_large_payload_is_rejected_before_allocation(self, limit):
        raw = Mock()
        raw.readline.return_value = b'$900000000'
        buffer = BoundedRedisBuffer(raw)
        with self.assertRaises(DataFactoryError):
            buffer.readline()
        raw.read.assert_not_called()

    def test_expired_protocol_pool_is_fenced_until_borrower_finishes_then_physically_closed(self):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
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
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
        busy = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 1, dispose=Mock()))
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
        idle = SimpleNamespace(dispose=Mock(), pool=SimpleNamespace(checkedout=lambda: 0, dispose=Mock()))
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
