import atexit
import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from urllib.error import HTTPError

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService


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
                     getattr(target, 'redis_db', None), target.extra_config, protocol, policy.pool_size]
        key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        while True:
            building = False
            with cls._lock:
                if cls._pid != os.getpid():
                    cls._entries, cls._pid, cls._thread, cls._building = {}, os.getpid(), None, set()
                cls.prune(policy.pool_idle_seconds)
                entry = cls._entries.get(key)
                if (entry is not None and not entry.get('broken')
                        and entry['active'] < entry['capacity']):
                    entry['active'] += 1
                    break
                if key not in cls._building and entry is None:
                    if len(cls._entries) + len(cls._building) >= policy.max_local_pools:
                        cls.prune(0)
                    if len(cls._entries) + len(cls._building) < policy.max_local_pools:
                        cls._building.add(key)
                        building = True
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
                        target, kind=DatasourcePermitKindEnum.CONNECTION, cost=size))
                    client = factory(size)
                except BaseException as error:
                    try:
                        for permit in permits:
                            DatasourceGovernorService.finish_operation(permit, failure=error)
                    finally:
                        with cls._lock:
                            cls._building.discard(key)
                    raise
                with cls._lock:
                    entry = {'client': client, 'permits': permits, 'active': 1, 'capacity': size, 'group': group,
                             'used': time.monotonic(), 'broken': False}
                    cls._entries[key] = entry
                    cls._building.discard(key)
                break
            DatasourceWaitService.pause()
        with cls._lock:
            if cls._thread is None:
                cls._thread = threading.Thread(target=cls.reap, name='datasource-protocol-reaper', daemon=True)
                cls._thread.start()
        broken = False
        failure = None
        try:
            yield entry['client']
        except BaseException as error:
            failure = error
            # 完整读取后的 404 是正常的文档不存在响应，不应反复销毁连接池。
            broken = not isinstance(error, HTTPError)
            raise
        finally:
            with cls._lock:
                entry['active'] -= 1
                entry['used'] = time.monotonic()
                entry['broken'] = entry['broken'] or broken
                if entry['broken']:
                    entry['used'] = 0
                try:
                    cls.prune(policy.pool_idle_seconds)
                except Exception:
                    if failure is None:
                        raise
                    failure._datasource_settlement_failed = True

    @classmethod
    def prune(cls, idle):
        for key, entry in list(cls._entries.items()):
            if not entry['active'] and time.monotonic() - entry['used'] >= idle:
                try:
                    entry['client'].close()
                except Exception as error:
                    for permit in entry['permits']:
                        DatasourceGovernorService.finish_operation(permit, unknown=True, failure=error)
                    raise
                # 先保存全部关闭证明，即使第一个控制面写失败，也不能遗失剩余名额。
                cls._entries.pop(key, None)
                DatasourceGovernorService.connections_closed(entry['permits'])

    @classmethod
    def relieve_pressure(cls, group):
        with cls._lock:
            for entry in cls._entries.values():
                if entry.get('group') == group and not entry['active']:
                    entry['used'] = 0
            cls.prune(DatasourceGovernorService.policy().pool_idle_seconds)

    @classmethod
    def close_all(cls):
        with cls._lock:
            cls.prune(0)

    @classmethod
    def reap(cls):
        from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
        renewed = 0
        while cls._pid == os.getpid():
            time.sleep(5)
            def maintain():
                nonlocal renewed
                with cls._lock:
                    DatasourceGovernorService.flush_pending_releases()
                    DatasourceGovernorService.flush_closed_connections()
                    cls.prune(DatasourceGovernorService.policy().pool_idle_seconds)
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
        with cls._lock:
            stale = DatasourceGovernorService.renew_connections(
                [permit for entry in cls._entries.values() for permit in entry['permits']])
            if stale:
                for entry in cls._entries.values():
                    if any(permit in stale for permit in entry['permits']):
                        entry['broken'], entry['used'] = True, 0
                cls.prune(0)


atexit.register(ProtocolPoolRegistry.close_all)
