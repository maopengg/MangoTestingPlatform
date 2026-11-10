from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic
import os
import threading


_wait_pulse = ContextVar('datasource_wait_pulse', default=None)
_wait_elapsed = ContextVar('datasource_wait_elapsed', default=0.0)
_wait_renewed = ContextVar('datasource_wait_renewed', default=0.0)


class DatasourceAdmissionProbeService:
    """仅合并本进程拥堵轮询，不保存名额，不得作为安全准入依据。"""
    _lock = threading.Lock()
    _due = {}
    _pid = None

    @classmethod
    def delay(cls, group, owner):
        with cls._lock:
            if cls._pid != os.getpid():
                cls._due, cls._pid = {}, os.getpid()
            if group not in cls._due:
                return 0
            entry = cls._due[group]
            if owner not in entry['owners']:
                return 0
            now = monotonic()
            head = min(entry['owners'], key=lambda key: (entry['owners'][key], key))
            remaining = entry['due'] - now
            if remaining <= 0 and owner == head:
                entry['due'] = now + 0.25
                return 0
            return max(0.05, min(0.25, remaining))

    @classmethod
    def congested(cls, group, owner, queued_at):
        with cls._lock:
            if len(cls._due) >= 256 and group not in cls._due:
                cls._due.pop(next(iter(cls._due)))
            entry = cls._due.setdefault(group, {'due': monotonic() + 0.25, 'owners': {}})
            if len(entry['owners']) < 256:
                entry['owners'].setdefault(owner, queued_at)

    @classmethod
    def finished(cls, group, owner):
        with cls._lock:
            entry = cls._due.get(group)
            if entry is not None:
                entry['owners'].pop(owner, None)
                entry['due'] = 0
                if not entry['owners']:
                    cls._due.pop(group, None)

    @classmethod
    def changed(cls, group):
        with cls._lock:
            for key in list(cls._due):
                if key[0] == group:
                    cls._due[key]['due'] = 0


class DatasourceWaitService:
    """资源等待不执行业务操作；让出 Case 线程并维护原执行者的所有权。"""

    @staticmethod
    @contextmanager
    def owner(pulse):
        from src.apps.data_factory.services.datasource_timing import DatasourceTimingService
        token = _wait_pulse.set(pulse)
        elapsed = _wait_elapsed.set(0.0)
        renewed = _wait_renewed.set(0.0)
        try:
            with DatasourceTimingService.scope():
                yield
        finally:
            _wait_renewed.reset(renewed)
            _wait_elapsed.reset(elapsed)
            _wait_pulse.reset(token)

    @staticmethod
    def elapsed():
        return _wait_elapsed.get()

    @staticmethod
    @contextmanager
    def control_io():
        from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
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
    def pause(seconds=0.1, *, renew_operation=True):
        from src.apps.task_center.services.execution.cooperative_executor import wait_until
        from src.apps.data_factory.services.cleanup_persistence import CleanupPersistenceService
        from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
        started = monotonic()
        wait_before, timing_before = _wait_elapsed.get(), Timing.snapshot()
        CleanupPersistenceService.check()
        if renew_operation and started - _wait_renewed.get() >= 5:
            from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
            DatasourceGovernorService.renew_waiting_operation()
            _wait_renewed.set(started)
        pulse = _wait_pulse.get()
        if pulse is not None:
            pulse()
        due = monotonic() + seconds
        resumed = [0.0]
        # ready 在调度 greenlet 中也会调用，不能在其中访问 Case 的 ContextVar。
        try:
            wait_until(lambda: monotonic() >= due, seconds + 1, interval=seconds,
                       on_resume=lambda: resumed.__setitem__(0, max(0, monotonic() - due)))
        finally:
            elapsed = monotonic() - started
            nested_wait = max(0, _wait_elapsed.get() - wait_before)
            _wait_elapsed.set(_wait_elapsed.get() + max(0, elapsed - nested_wait))
            own_time = max(0, elapsed - sum(Timing.delta(timing_before).values()) / 1000)
            Timing.waited(own_time, min(own_time, resumed[0]))
