import atexit
import os
import threading
import time
import uuid

from sqlalchemy import exc
from sqlalchemy.pool import QueuePool

from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
from src.apps.data_factory.services.datasource_timing import DatasourceTimingService


class DatasourceQueuePool(QueuePool):
    def _do_get(self):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
        from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
        started = time.monotonic()
        next_log = started + 30
        wait_id = uuid.uuid4().hex
        while True:
            try:
                return super()._do_get()
            except exc.TimeoutError as error:
                # 只处理本地 QueuePool 的容量等待，驱动连接/SQL 超时不得重试。
                if error.code != '3o7r':
                    raise
            next_log = Timing.diagnose(started, next_log, phase=Phase.LOCAL_POOL,
                                      database_id=getattr(self, '_mango_database_id', None), wait_id=wait_id,
                                      group=getattr(self, '_mango_instance_group', None), wait_kind='capacity',
                                      checked_out=self.checkedout(), pool_size=self.size())
            with Timing.waiting(Phase.LOCAL_POOL):
                DatasourceWaitService.pause()


class DatasourcePoolRegistry:
    """进程内共享引擎；实例级连接总额由 governor 另行约束。"""
    _lock = threading.RLock()
    _engines = {}
    _pid = None
    _reaper = None

    @classmethod
    def get_engine(cls, target, timeout, builder):
        policy = DatasourceGovernorService.policy()
        key = (target.cache_key, timeout, policy.pool_size)
        with DatasourceTimingService.locked(cls._lock):
            if cls._pid != os.getpid():
                # fork 不得关闭父进程的在用 socket，也不得复用它们。
                for engine, dispose, _, _ in cls._engines.values():
                    dispose(close=False)
                cls._engines = {}
                cls._pid, cls._reaper = os.getpid(), None
            cls.prune(policy.pool_idle_seconds)
            for old_key, (old_engine, old_dispose, _, borrowers) in list(cls._engines.items()):
                if old_key[0] == key[0] and old_key != key and old_engine.pool.checkedout() == 0:
                    old_dispose()
                    if not borrowers:
                        cls._engines.pop(old_key, None)
            if key in cls._engines:
                engine, dispose, _, borrowers = cls._engines[key]
                cls._engines[key] = engine, dispose, time.monotonic(), borrowers + 1
                return engine
            if len(cls._engines) >= policy.max_local_pools:
                cls.prune(0)
            # 上限用于闲置缓存；活跃 Case 缓存的引擎句柄不占物理连接名额。
            # 不能让同一 Case 等自己释放旧句柄后才允许打开另一个数据源。
            engine = builder(policy)
            engine._mango_pool_size = policy.pool_size
            engine._mango_instance_group = DatasourceGovernorService.target_policy(target, policy)[2]
            engine.pool._mango_instance_group = engine._mango_instance_group
            dispose = engine.dispose
            cls._engines[key] = engine, dispose, time.monotonic(), 1
            # 既有调用方的 dispose 表示租借结束，不销毁其他线程共享的真实池。
            engine.dispose = lambda *args, **kwargs: cls.touch(key)
            if cls._reaper is None:
                cls._reaper = threading.Thread(target=cls.reap, name='datasource-pool-reaper', daemon=True)
                cls._reaper.start()
            return engine

    @classmethod
    def touch(cls, key):
        with DatasourceTimingService.locked(cls._lock):
            if key in cls._engines:
                engine, dispose, _, borrowers = cls._engines[key]
                cls._engines[key] = engine, dispose, time.monotonic(), max(0, borrowers - 1)
                if len(cls._engines) > DatasourceGovernorService.policy().max_local_pools:
                    cls.prune(0)

    @classmethod
    def relieve_pressure(cls, group):
        with DatasourceTimingService.locked(cls._lock):
            for key, (engine, dispose, _, borrowers) in list(cls._engines.items()):
                if getattr(engine, '_mango_instance_group', None) == group and engine.pool.checkedout() == 0:
                    dispose()
                    if not borrowers:
                        cls._engines.pop(key, None)

    @classmethod
    def prune(cls, idle):
        for key, (engine, dispose, used, borrowers) in list(cls._engines.items()):
            if time.monotonic() - used >= idle and engine.pool.checkedout() == 0:
                dispose()
                if borrowers == 0:
                    cls._engines.pop(key, None)
                else:
                    cls._engines[key] = engine, dispose, time.monotonic(), borrowers

    @classmethod
    def reap(cls):
        from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
        renewed = 0
        while cls._pid == os.getpid():
            time.sleep(5)
            def maintain():
                nonlocal renewed
                # 控制库可能排队或断连；不能持注册表锁等待，否则所有借还池都会被拖住。
                DatasourceGovernorService.flush_pending_releases()
                DatasourceGovernorService.flush_closed_connections()
                policy = DatasourceGovernorService.policy()
                with DatasourceTimingService.locked(cls._lock):
                    cls.prune(policy.pool_idle_seconds)
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
        from src.apps.data_factory.services.datasource_connection import GovernedDbapiConnection
        stale = DatasourceGovernorService.renew_connections(GovernedDbapiConnection.live_permits())
        # 不复活过期租约；仅关闭闲置池的真实连接，再按 close 证明核销。
        # checkedout 中的操作必须自行完成/回滚，不能由维护线程中断。
        for group in {permit[0] for permit in stale}:
            cls.relieve_pressure(group)

    @classmethod
    def close_all(cls):
        with DatasourceTimingService.locked(cls._lock):
            cls.prune(0)


atexit.register(DatasourcePoolRegistry.close_all)
