import atexit
import os
import threading
import time
import uuid
from collections import deque
from contextvars import ContextVar

from sqlalchemy import event, exc
from sqlalchemy.pool import QueuePool

from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService

_checkout_turn = ContextVar('datasource_pool_checkout_turn', default=None)


class DatasourceQueuePool(QueuePool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._admission_lock = threading.Lock()
        self._admission_queue = deque()
        for name, callback in (('checkout', self._connection_checkout), ('checkin', self._connection_checkin)):
            if not event.contains(self, name, callback):
                event.listen(self, name, callback)

    @staticmethod
    def _connection_checkout(connection, record, proxy):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        DatasourceWaitService.release_connection(getattr(record, '_mango_connection_hold', None))
        record._mango_connection_hold = DatasourceWaitService.hold_connection()

    @staticmethod
    def _connection_checkin(connection, record):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        DatasourceWaitService.release_connection(getattr(record, '_mango_connection_hold', None))
        record._mango_connection_hold = None

    def _create_connection(self):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        turn = _checkout_turn.get()
        if turn is not None and turn[0] is self:
            # QueuePool 已原子保留创建容量；后续慢连接不能阻止其他等待者复用归还的连接。
            self._finish_turn(turn[1])
        # QueuePool 已为创建过程保留池容量，等待物理连接配额时同样不能释放执行位。
        with DatasourceWaitService.connection_scope():
            return super()._create_connection()

    def _finish_turn(self, ticket):
        with self._admission_lock:
            if ticket in self._admission_queue:
                self._admission_queue.remove(ticket)
                if self._admission_queue:
                    self._admission_queue[0].set()

    def _do_return_conn(self, record):
        super()._do_return_conn(record)
        with self._admission_lock:
            if self._admission_queue:
                self._admission_queue[0].set()

    def _do_get(self):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing
        from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
        started = time.monotonic()
        next_log = started + 30
        wait_id = uuid.uuid4().hex
        ticket = threading.Event()
        with self._admission_lock:
            self._admission_queue.append(ticket)
        token = _checkout_turn.set((self, ticket))
        try:
            while True:
                with self._admission_lock:
                    first = self._admission_queue[0] is ticket
                    ticket.clear()
                if first:
                    try:
                        return super()._do_get()
                    except exc.TimeoutError as error:
                        # 只处理本地容量等待，驱动连接/SQL 超时不得重试。
                        if error.code != '3o7r':
                            raise
                if not DatasourceGovernorService.admission_wait_enabled():
                    raise exc.TimeoutError('Datasource pool capacity is unavailable', code='3o7r')
                next_log = Timing.diagnose(started, next_log, phase=Phase.LOCAL_POOL,
                                          database_id=getattr(self, '_mango_database_id', None), wait_id=wait_id,
                                          group=getattr(self, '_mango_instance_group', None), wait_kind='capacity',
                                          checked_out=self.checkedout(), pool_size=self.size())
                with Timing.waiting(Phase.LOCAL_POOL):
                    DatasourceWaitService.pause(ready=ticket.is_set)
        finally:
            _checkout_turn.reset(token)
            self._finish_turn(ticket)


class DatasourcePoolRegistry:
    """进程内共享引擎；实例级连接总额由 governor 另行约束。"""
    _lock = threading.RLock()
    _engines = {}
    _pid = None
    _reaper = None

    @classmethod
    def detach_locked(cls, key):
        engine, dispose, _, borrowers = cls._engines[key]
        if engine.pool.checkedout():
            return []
        if not borrowers:
            cls._engines.pop(key)
            return [dispose]
        # 仍有调用方持有引擎句柄；锁内换新池，锁外关闭旧池，避免并发借用正在退休的池。
        retired = engine.pool
        dispose(close=False)
        cls._engines[key] = engine, dispose, time.monotonic(), borrowers
        return [retired.dispose]

    @classmethod
    def collect_locked(cls, idle):
        callbacks = []
        for key, (engine, _, used, _) in list(cls._engines.items()):
            if time.monotonic() - used >= idle and engine.pool.checkedout() == 0:
                callbacks.extend(cls.detach_locked(key))
        return callbacks

    @staticmethod
    def close_detached(callbacks):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        for callback in callbacks:
            try:
                with DatasourceInfrastructureService.maintenance_scope():
                    callback()
            except Exception:
                from src.common.logging import log
                log.system.exception('event=datasource_detached_sql_pool_close_failed action=retain_connection_evidence')

    @classmethod
    def get_engine(cls, target, timeout, builder):
        policy = DatasourceGovernorService.policy()
        group = DatasourceGovernorService.target_policy(target, policy)[2]
        key = (target.cache_key, timeout, policy.pool_size, DatasourceGovernorService.lane().value)
        callbacks = []
        try:
            with DatasourceTimingService.locked(cls._lock):
                if cls._pid != os.getpid():
                    for _, dispose, _, _ in cls._engines.values():
                        dispose(close=False)
                    cls._engines = {}
                    cls._pid, cls._reaper = os.getpid(), None
                callbacks.extend(cls.collect_locked(policy.pool_idle_seconds))
                for old_key, (old_engine, _, _, _) in list(cls._engines.items()):
                    if old_key[0] == key[0] and old_key != key and old_engine.pool.checkedout() == 0:
                        callbacks.extend(cls.detach_locked(old_key))
                if key in cls._engines:
                    engine, dispose, _, borrowers = cls._engines[key]
                    cls._engines[key] = engine, dispose, time.monotonic(), borrowers + 1
                else:
                    if len(cls._engines) >= policy.max_local_pools:
                        callbacks.extend(cls.collect_locked(0))
                    # builder 只构造惰性引擎，不连接数据源；物理建连仍在锁外 checkout。
                    engine = builder(policy)
                    engine._mango_pool_size = policy.pool_size
                    engine._mango_instance_group = group
                    engine.pool._mango_instance_group = group
                    dispose = engine.dispose
                    cls._engines[key] = engine, dispose, time.monotonic(), 1
                    engine.dispose = lambda *args, **kwargs: cls.touch(key, engine)
                if cls._reaper is None:
                    cls._reaper = threading.Thread(target=cls.reap, name='datasource-pool-reaper', daemon=True)
                    cls._reaper.start()
        finally:
            cls.close_detached(callbacks)
        return engine

    @classmethod
    def touch(cls, key, expected_engine):
        policy = DatasourceGovernorService.policy()
        callbacks = []
        with DatasourceTimingService.locked(cls._lock):
            if key in cls._engines and cls._engines[key][0] is expected_engine:
                engine, dispose, _, borrowers = cls._engines[key]
                cls._engines[key] = engine, dispose, time.monotonic(), max(0, borrowers - 1)
                if len(cls._engines) > policy.max_local_pools:
                    callbacks = cls.collect_locked(0)
        cls.close_detached(callbacks)

    @classmethod
    def relieve_pressure(cls, group):
        callbacks = []
        with DatasourceTimingService.locked(cls._lock):
            for key, (engine, _, _, _) in list(cls._engines.items()):
                if getattr(engine, '_mango_instance_group', None) == group and engine.pool.checkedout() == 0:
                    callbacks.extend(cls.detach_locked(key))
        cls.close_detached(callbacks)

    @classmethod
    def prune(cls, idle):
        with DatasourceTimingService.locked(cls._lock):
            callbacks = cls.collect_locked(idle)
        cls.close_detached(callbacks)

    @classmethod
    def reap(cls):
        from src.apps.data_factory.services.pool.pool_maintenance import DatasourcePoolMaintenance
        renewed = 0
        while cls._pid == os.getpid():
            time.sleep(5)
            def maintain():
                nonlocal renewed
                # 控制库可能排队或断连；不能持注册表锁等待，否则所有借还池都会被拖住。
                DatasourceGovernorService.flush_pending_releases()
                DatasourceGovernorService.flush_closed_connections()
                policy = DatasourceGovernorService.policy()
                cls.prune(policy.pool_idle_seconds)
                with DatasourceTimingService.locked(cls._lock):
                    groups = {getattr(engine, '_mango_instance_group', None)
                              for engine, _, _, _ in cls._engines.values()}
                for group in groups - {None}:
                    if DatasourceGovernorService.connection_pressure(group):
                        cls.relieve_pressure(group)
                if time.monotonic() - renewed >= 15:
                    cls.renew_live_connections()
                    renewed = time.monotonic()
            DatasourcePoolMaintenance.run('sql', maintain)

    @classmethod
    def renew_live_connections(cls):
        from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
        stale = DatasourceGovernorService.renew_connections(GovernedDbapiConnection.live_permits())
        # 不复活过期租约；仅关闭闲置池的真实连接，再按 close 证明核销。
        # checkedout 中的操作必须自行完成/回滚，不能由维护线程中断。
        for group in {permit[0] for permit in stale}:
            cls.relieve_pressure(group)

    @classmethod
    def close_all(cls):
        cls.prune(0)


atexit.register(DatasourcePoolRegistry.close_all)
