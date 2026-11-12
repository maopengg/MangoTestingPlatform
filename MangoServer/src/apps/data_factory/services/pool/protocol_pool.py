import atexit
import hashlib
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from urllib.error import HTTPError

from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService


class ProtocolPoolRegistry:
    _lock = threading.RLock()
    _entries = {}
    _pid = None
    _thread = None
    _building = set()

    @classmethod
    @contextmanager
    def borrow(cls, target, protocol, factory):
        policy = DatasourceGovernorService.policy()
        signature = [target.id, str(target.update_time), target.user, target.host, target.port,
                     getattr(target, 'redis_db', None), target.extra_config, protocol, policy.pool_size,
                     DatasourceGovernorService.lane().value]
        key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing
        from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
        started = time.monotonic()
        next_log = started + 30
        wait_id = uuid.uuid4().hex
        group = DatasourceGovernorService.target_policy(target, policy)[2]
        while True:
            building = False
            borrowed = False
            with DatasourceTimingService.locked(cls._lock):
                if cls._pid != os.getpid():
                    cls._entries, cls._pid, cls._thread, cls._building = {}, os.getpid(), None, set()
                retired = cls.collect_locked(policy.pool_idle_seconds)
                entry = cls._entries.get(key)
                if (entry is not None and not entry.get('broken')
                        and entry['active'] < entry['capacity']):
                    entry['active'] += 1
                    borrowed = True
                elif key not in cls._building and entry is None:
                    if len(cls._entries) + len(cls._building) >= policy.max_local_pools:
                        retired.extend(cls.collect_locked(0))
                    cls._building.add(key)
                    building = True
            cls.close_detached(retired)
            if borrowed:
                break
            if building:
                permits = []
                try:
                    _, budget, group = DatasourceGovernorService.target_policy(target, policy)
                    from src.apps.data_factory.enums.performance import DatasourceQueueLaneEnum
                    size = policy.pool_size
                    if budget is not None and DatasourceGovernorService.lane() != DatasourceQueueLaneEnum.CLEANUP:
                        size = min(size, budget.connections - policy.pool_size)
                    # 整池原子预留，不逐个占有一半连接再互相等待；等待时不持注册表锁。
                    permits.append(DatasourceGovernorService.acquire(
                        target, cost=size))
                    client = factory(size)
                except BaseException as error:
                    try:
                        for permit in permits:
                            DatasourceGovernorService.finish_connection(permit, failure=error)
                    finally:
                        with DatasourceTimingService.locked(cls._lock):
                            cls._building.discard(key)
                    raise
                with DatasourceTimingService.locked(cls._lock):
                    entry = {'client': client, 'permits': permits, 'active': 1, 'capacity': size, 'group': group,
                             'used': time.monotonic(), 'broken': False}
                    cls._entries[key] = entry
                    cls._building.discard(key)
                break
            next_log = Timing.diagnose(started, next_log, phase=Phase.LOCAL_POOL,
                                      database_id=target.id, wait_id=wait_id, group=group)
            with Timing.waiting(Phase.LOCAL_POOL):
                DatasourceWaitService.pause()
        with DatasourceTimingService.locked(cls._lock):
            if cls._thread is None:
                cls._thread = threading.Thread(target=cls.reap, name='datasource-protocol-reaper', daemon=True)
                cls._thread.start()
        broken = False
        try:
            yield entry['client']
        except BaseException as error:
            # 完整读取后的 404 是正常的文档不存在响应，不应反复销毁连接池。
            broken = not isinstance(error, HTTPError)
            raise
        finally:
            with DatasourceTimingService.locked(cls._lock):
                entry['active'] -= 1
                entry['used'] = time.monotonic()
                entry['broken'] = entry['broken'] or broken
                if entry['broken']:
                    entry['used'] = 0
                retired = cls.collect_locked(policy.pool_idle_seconds)
            cls.close_detached(retired)

    @classmethod
    def collect_locked(cls, idle, *, group=None):
        retired = []
        for key, entry in list(cls._entries.items()):
            if (not entry['active'] and time.monotonic() - entry['used'] >= idle
                    and (group is None or entry.get('group') == group)):
                retired.append(cls._entries.pop(key))
        return retired

    @staticmethod
    def close_detached(retired):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        for entry in retired:
            with DatasourceInfrastructureService.maintenance_scope():
                try:
                    entry['client'].close()
                except Exception as error:
                    for permit in entry['permits']:
                        DatasourceGovernorService.finish_connection(permit, unknown=True, failure=error)
                    from src.common.logging import log
                    log.system.warning('event=datasource_idle_protocol_close_unknown group=%s '
                                       'action=retain_connection_for_review', entry['group'])
                else:
                    DatasourceGovernorService.connections_closed(entry['permits'])

    @classmethod
    def prune(cls, idle):
        with DatasourceTimingService.locked(cls._lock):
            retired = cls.collect_locked(idle)
        cls.close_detached(retired)

    @classmethod
    def relieve_pressure(cls, group):
        with DatasourceTimingService.locked(cls._lock):
            for entry in cls._entries.values():
                if entry.get('group') == group and not entry['active']:
                    entry['used'] = 0
            retired = cls.collect_locked(0, group=group)
        cls.close_detached(retired)

    @classmethod
    def close_all(cls):
        cls.prune(0)

    @classmethod
    def reap(cls):
        from src.apps.data_factory.services.pool.pool_maintenance import DatasourcePoolMaintenance
        renewed = 0
        while cls._pid == os.getpid():
            time.sleep(5)
            def maintain():
                nonlocal renewed
                DatasourceGovernorService.flush_pending_releases()
                DatasourceGovernorService.flush_closed_connections()
                policy = DatasourceGovernorService.policy()
                cls.prune(policy.pool_idle_seconds)
                with DatasourceTimingService.locked(cls._lock):
                    groups = {entry.get('group') for entry in cls._entries.values()} - {None}
                for group in groups:
                    if DatasourceGovernorService.connection_pressure(group):
                        cls.relieve_pressure(group)
                if time.monotonic() - renewed >= 15:
                    cls.renew_live_connections()
                    renewed = time.monotonic()
            DatasourcePoolMaintenance.run('protocol', maintain)

    @classmethod
    def renew_live_connections(cls):
        with DatasourceTimingService.locked(cls._lock):
            permits = [permit for entry in cls._entries.values() for permit in entry['permits']]
        # 网络续期只处理快照中的精确 owner；新借用不扩大配额，也不等待该注册表锁。
        stale = DatasourceGovernorService.renew_connections(permits)
        with DatasourceTimingService.locked(cls._lock):
            if stale:
                for entry in cls._entries.values():
                    if any(permit in stale for permit in entry['permits']):
                        entry['broken'], entry['used'] = True, 0
            retired = cls.collect_locked(0) if stale else []
        cls.close_detached(retired)


atexit.register(ProtocolPoolRegistry.close_all)
