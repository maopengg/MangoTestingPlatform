from src.apps.auto_api.exceptions import API_CONCURRENCY_LIMIT_EXCEEDED
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.exceptions import (
    TASK_API_CONCURRENCY_INVALID,
    TaskCenterError,
)
from src.common.exceptions import MangoServerError
from src.common.logging import log


class ApiConcurrencyService:
    @classmethod
    def capacity(cls) -> dict:
        worker_limit = SystemConfigService.get_api_worker_thread_pool_size()
        try:
            worker_count = ServiceHeartbeatService.count_online_instances(RuntimeServiceName.API_WORKER)
        except Exception as error:
            log.system.warning(f'读取在线 API Worker 数量失败，按单节点容量兜底：{error}')
            worker_count = 0
        platform_limit = max(1, worker_count or 1) * worker_limit
        return {
            'online_api_worker_count': worker_count,
            'api_worker_thread_pool_size': worker_limit,
            'api_platform_limit': platform_limit,
        }

    @classmethod
    def platform_limit(cls) -> int:
        return cls.capacity()['api_platform_limit']

    @classmethod
    def validate_optional(
            cls,
            value,
            error_cls: type[MangoServerError] = TaskCenterError,
            platform_limit: int | None = None,
    ) -> int | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, bool) or isinstance(value, float):
            raise error_cls(TASK_API_CONCURRENCY_INVALID)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized.isdigit():
                raise error_cls(TASK_API_CONCURRENCY_INVALID)
            value = normalized
        try:
            limit = int(value)
        except (TypeError, ValueError) as error:
            raise error_cls(TASK_API_CONCURRENCY_INVALID, error=str(error)) from error
        if limit < 1:
            raise error_cls(TASK_API_CONCURRENCY_INVALID)
        current_platform_limit = platform_limit or cls.platform_limit()
        if limit > current_platform_limit:
            raise error_cls(API_CONCURRENCY_LIMIT_EXCEEDED, value=(current_platform_limit,))
        return limit

    @classmethod
    def resolve_report_limit(
            cls,
            value=None,
            error_cls: type[MangoServerError] = TaskCenterError,
    ) -> int:
        platform_limit = cls.platform_limit()
        return cls.validate_optional(value, error_cls, platform_limit) or platform_limit

    @classmethod
    def resolve_task_trigger_limit(
            cls,
            task_limit,
            override=None,
            override_provided: bool = False,
            error_cls: type[MangoServerError] = TaskCenterError,
    ) -> int:
        platform_limit = cls.platform_limit()
        if override_provided and override not in (None, ''):
            return cls.validate_optional(override, error_cls, platform_limit) or platform_limit
        if task_limit:
            normalized_task_limit = max(1, int(task_limit))
            if normalized_task_limit > platform_limit:
                log.system.warning(
                    f'定时任务配置并发{normalized_task_limit}超过当前平台容量{platform_limit}，'
                    f'本次按平台容量执行'
                )
            return min(normalized_task_limit, platform_limit)
        return platform_limit

    @classmethod
    def clamp_snapshot_limit(cls, value, platform_limit: int | None = None) -> int:
        current_platform_limit = platform_limit or cls.platform_limit()
        try:
            limit = int(value) if value is not None else current_platform_limit
        except (TypeError, ValueError):
            limit = current_platform_limit
        return max(1, min(limit, current_platform_limit))
