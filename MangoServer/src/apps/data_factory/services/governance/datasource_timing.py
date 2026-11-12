"""执行上下文内累计计时；不保存 SQL、参数、连接地址或凭据。"""
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic

from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase

log = logging.getLogger(__name__)
_timings = ContextVar('datasource_timings', default=None)
_phase = ContextVar('datasource_wait_phase', default=Phase.CONNECTION_SLOT)


class DatasourceTimingService:
    @staticmethod
    def snapshot():
        return dict(_timings.get() or {})

    @staticmethod
    @contextmanager
    def scope():
        token = _timings.set({})
        try:
            yield
        finally:
            _timings.reset(token)

    @staticmethod
    def add(phase, seconds):
        values = DatasourceTimingService.snapshot()
        key = phase.value if isinstance(phase, Phase) else phase
        values[key] = values.get(key, 0) + max(0, seconds) * 1000
        _timings.set(values)

    @staticmethod
    def delta(start):
        return {key: round(max(0, value - start.get(key, 0)), 2)
                for key, value in DatasourceTimingService.snapshot().items()}

    @staticmethod
    @contextmanager
    def measure(phase):
        started = monotonic()
        before = DatasourceTimingService.snapshot()
        try:
            yield
        finally:
            nested_ms = sum(DatasourceTimingService.delta(before).values())
            DatasourceTimingService.add(phase, max(0, monotonic() - started - nested_ms / 1000))

    @staticmethod
    @contextmanager
    def waiting(phase):
        token = _phase.set(phase)
        try:
            yield
        finally:
            _phase.reset(token)

    @staticmethod
    @contextmanager
    def locked(lock):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        started = monotonic()
        next_log = started + 30
        while not lock.acquire(blocking=False):
            next_log = DatasourceTimingService.diagnose(started, next_log, phase=Phase.LOCAL_POOL,
                                                       wait_kind='registry_lock')
            with DatasourceTimingService.waiting(Phase.LOCAL_POOL):
                DatasourceWaitService.pause(0.01)
        try:
            yield
        finally:
            lock.release()

    @staticmethod
    def waited(seconds, resume_seconds):
        DatasourceTimingService.add(_phase.get(), max(0, seconds - resume_seconds))
        DatasourceTimingService.add(Phase.SCHEDULER_RESUME, resume_seconds)

    @staticmethod
    def diagnose(started, next_log, *, phase, database_id=None, wait_id=None, group=None,
                 wait_kind=None, checked_out=None, pool_size=None):
        now = monotonic()
        if now < next_log:
            return next_log
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
        handle = Audit.active()
        if database_id is None:
            database_id = getattr(getattr(handle, 'record', None), 'database_id', None)
        source = Audit.current_source()
        # 只允许稳定的来源标识进入日志，不序列化整个 source_detail。
        context = {key: source[key] for key in (
            'case_id', 'case_source_id', 'execution_id', 'source_id', 'test_env', 'source_stage',
        ) if key in source and isinstance(source[key], (int, str))}
        log.warning('event=datasource_long_wait request_id=%s wait_id=%s database_id=%s group=%s '
                  'phase=%s wait_kind=%s checked_out=%s pool_size=%s elapsed_ms=%.2f context=%s',
                  getattr(getattr(handle, 'record', None), 'request_id', None), wait_id,
                  database_id, group, phase.value, wait_kind, checked_out, pool_size,
                  (now - started) * 1000, context)
        return now + 30
