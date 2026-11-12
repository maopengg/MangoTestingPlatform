from contextlib import contextmanager
from contextvars import ContextVar

from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService

_cleanup_lease = ContextVar('data_factory_cleanup_lease', default=None)


class CleanupPersistenceService:
    @staticmethod
    @contextmanager
    def lease(lease):
        token = _cleanup_lease.set(lease)
        try:
            yield
        finally:
            _cleanup_lease.reset(token)

    @staticmethod
    def write(callback):
        lease = _cleanup_lease.get()
        if lease is None:
            return callback()
        from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
        accepted, result = ExecutorTaskService.with_cleanup_lease(lease, callback)
        if not accepted:
            raise DatasourceInfrastructureService.cleanup_error('清理任务已由其他执行进程接管，当前进程已停止处理。请查看该任务的最新清理状态', task_id=getattr(lease, 'task_id', None))
        return result

    @classmethod
    def check(cls):
        cls.write(lambda: True)

    @classmethod
    def save(cls, instance, fields=None):
        cls.write(lambda: instance.save(update_fields=fields) if fields else instance.save())
