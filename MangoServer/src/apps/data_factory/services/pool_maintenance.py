import os
import threading
import time


class DatasourcePoolMaintenance:
    """进程内维护健康与日志合并，不替代持久名额或未知结果责任。"""
    _lock = threading.RLock()
    _states = {}
    _pid = None

    @classmethod
    def close_idle_pools(cls):
        from src.apps.data_factory.services.datasource_pool import DatasourcePoolRegistry
        from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
        # 只关闭闲置物理连接，并结算已有精确关闭证明；不碰在用连接或未知操作占用。
        for name, callback in (
            ('sql_shutdown', DatasourcePoolRegistry.close_all),
            ('protocol_shutdown', ProtocolPoolRegistry.close_all),
            ('connection_settlement', DatasourceGovernorService.flush_closed_connections),
            ('operation_settlement', DatasourceGovernorService.flush_pending_releases),
        ):
            cls.run(name, callback)

    @classmethod
    def run(cls, name, callback):
        from src.common.logging import log
        from django.db import close_old_connections
        with cls._lock:
            if cls._pid != os.getpid():
                cls._states, cls._pid = {}, os.getpid()
            state = cls._states.setdefault(name, {'success': 0, 'failures': 0, 'logged': 0})
        try:
            # 后台线程没有 HTTP 请求边界，配置读取的 default 连接同样需要生命周期管理。
            close_old_connections()
            callback()
        except Exception:
            with cls._lock:
                state['failures'] += 1
                now = time.monotonic()
                if state['failures'] == 1:
                    log.system.exception('数据源连接池维护失败：pool=%s', name)
                    state['logged'] = now
                elif now - state['logged'] >= 60:
                    log.system.error('数据源连接池维护持续失败：pool=%s, failures=%s', name, state['failures'])
                    state['logged'] = now
            return False
        with cls._lock:
            if state['failures']:
                log.system.info('数据源连接池维护已恢复：pool=%s, failures=%s', name, state['failures'])
            state['failures'] = 0
            state['success'] = time.monotonic()
        return True

    @classmethod
    def healthy(cls):
        with cls._lock:
            if cls._pid != os.getpid():
                return True
            now = time.monotonic()
            return all(not value['failures'] and value['success'] > 0
                       and now - value['success'] < 45 for value in cls._states.values())
