from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic
import threading


_wait_pulse = ContextVar('datasource_wait_pulse', default=None)
_wait_elapsed = ContextVar('datasource_wait_elapsed', default=0.0)
_connection_holds = ContextVar('datasource_connection_holds', default=())


class DatasourceWaitService:
    """资源等待不执行业务操作；让出 Case 线程并维护原执行者的所有权。"""

    @staticmethod
    @contextmanager
    def owner(pulse):
        from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService
        token = _wait_pulse.set(pulse)
        elapsed = _wait_elapsed.set(0.0)
        try:
            with DatasourceTimingService.scope():
                yield
        finally:
            _wait_elapsed.reset(elapsed)
            _wait_pulse.reset(token)

    @staticmethod
    def elapsed():
        return _wait_elapsed.get()

    @staticmethod
    def hold_connection():
        marker = threading.Event()
        marker.set()
        _connection_holds.set(tuple(value for value in _connection_holds.get() if value.is_set()) + (marker,))
        return marker

    @staticmethod
    def release_connection(marker):
        if marker is not None:
            # checkin 可能发生在失效连接的其他收尾上下文，共享标记使原上下文也能看到释放。
            marker.clear()
        _connection_holds.set(tuple(value for value in _connection_holds.get() if value.is_set()))

    @staticmethod
    def connection_held():
        return any(value.is_set() for value in _connection_holds.get())

    @staticmethod
    @contextmanager
    def connection_scope():
        marker = DatasourceWaitService.hold_connection()
        try:
            yield
        finally:
            DatasourceWaitService.release_connection(marker)

    @staticmethod
    @contextmanager
    def control_io():
        from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing
        from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
        started, waited = monotonic(), _wait_elapsed.get()
        try:
            with Timing.measure(Phase.CONTROL_IO):
                yield
        finally:
            # 控制库行锁/网络耗时也不是被测 SQL 耗时；嵌套退避已累计的部分不重复计算。
            nested = max(0, _wait_elapsed.get() - waited)
            _wait_elapsed.set(_wait_elapsed.get() + max(0, monotonic() - started - nested))

    @staticmethod
    def pause(seconds=0.1, *, ready=None):
        from src.apps.task_center.services.execution.cooperative_executor import wait_until
        from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
        from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing
        started = monotonic()
        wait_before, timing_before = _wait_elapsed.get(), Timing.snapshot()
        CleanupPersistenceService.check()
        pulse = _wait_pulse.get()
        if pulse is not None:
            pulse()
        due = monotonic() + seconds
        resumed = [0.0]
        # ready 在调度 greenlet 中也会调用，不能在其中访问 Case 的 ContextVar。
        try:
            wait_until(lambda: (ready is not None and ready()) or monotonic() >= due,
                       seconds + 1, interval=min(seconds, 0.1),
                       on_resume=lambda: resumed.__setitem__(0, max(0, monotonic() - due)))
        finally:
            elapsed = monotonic() - started
            nested_wait = max(0, _wait_elapsed.get() - wait_before)
            _wait_elapsed.set(_wait_elapsed.get() + max(0, elapsed - nested_wait))
            own_time = max(0, elapsed - sum(Timing.delta(timing_before).values()) / 1000)
            Timing.waited(own_time, min(own_time, resumed[0]))
