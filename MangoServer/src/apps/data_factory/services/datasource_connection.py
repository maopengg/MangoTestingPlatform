import os
import threading
import weakref

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService


class GovernedDbapiConnection:
    """将 socket 的配额生命周期绑定到真实 close，而非 SQLAlchemy 的 close 前事件。"""
    _lock = threading.RLock()
    _live = weakref.WeakSet()
    _pid = None

    def __init__(self, connection, permit):
        object.__setattr__(self, '_connection', connection)
        object.__setattr__(self, '_permit', permit)
        object.__setattr__(self, '_creator_pid', os.getpid())
        with self._lock:
            if self.__class__._pid != os.getpid():
                self.__class__._live = weakref.WeakSet()
                self.__class__._pid = os.getpid()
            self._live.add(self)

    def __del__(self):
        # 驱动对象被回收时也必须关闭物理连接并核销名额；不能只让 WeakSet 丢失持有者。
        # fork 子进程不得关闭或释放父进程的 socket/名额。
        if self.__dict__.get('_creator_pid') != os.getpid() or not self.__dict__.get('_permit'):
            return
        try:
            self.close()
        except Exception as error:
            # close 未确认时保留未知占用；控制面失败时精确关闭证明已登记到待核销集合。
            from src.common.logging import log
            log.system.error('数据源连接回收未完成，保留对应占用等待核查：exception_type=%s', type(error).__name__)

    @classmethod
    def live_permits(cls):
        with cls._lock:
            if cls._pid != os.getpid():
                return []
            return [value._permit for value in cls._live if value._permit is not None]

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._connection, name, value)

    def close(self):
        permit = self._permit
        if permit is None:
            return
        try:
            self._connection.close()
        except Exception as error:
            DatasourceGovernorService.finish_operation(permit, unknown=True, failure=error)
            raise
        else:
            object.__setattr__(self, '_permit', None)
            DatasourceGovernorService.connection_closed(permit)

    @classmethod
    def connect(cls, target, callback):
        permit = DatasourceGovernorService.acquire(target, kind=DatasourcePermitKindEnum.CONNECTION)
        try:
            from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
            from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
            with Timing.measure(Phase.CONNECT):
                connection = callback()
        except Exception as error:
            # 未拿到可用连接，不进行任何语句重放。
            DatasourceGovernorService.finish_operation(permit, failure=error)
            raise
        return cls(connection, permit) if permit is not None else connection
