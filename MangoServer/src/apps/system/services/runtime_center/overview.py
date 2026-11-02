import os
import socket

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.diagnostics import DiagnosticsService
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.queue_stats import QueueStatsService
from src.apps.system.services.runtime_center.recent_errors import RecentErrorsService
from src.apps.system.services.system_config import (
    API_WORKER_DESIRED_COUNT_DEFAULT,
    API_WORKER_DESIRED_COUNT_KEY,
    SystemConfigService,
)
from src.apps.user.services.permission import PermissionMenuService


class RuntimeOverviewService:
    SERVICE_NAMES = [
        RuntimeServiceName.CORE_API,
        RuntimeServiceName.SCHEDULER,
        RuntimeServiceName.API_WORKER,
        RuntimeServiceName.MCP,
        RuntimeServiceName.REALTIME,
        RuntimeServiceName.MONITORING,
    ]

    @classmethod
    def visible_overview(cls, user) -> dict:
        data = dict(cls.get_overview())
        # 汇总不能成为独立异常页面及运行详情权限的旁路。
        data.pop('recent_errors', None)
        permissions = PermissionMenuService.permission_keys_for_user(user) if user else set()
        if 'system.runtime_center:read' not in permissions:
            data['queues'] = {}
            data['diagnostics'] = []
            data['services'] = [
                {key: value for key, value in service.items() if key not in ('instances', 'metadata', 'log_query')}
                for service in data.get('services', [])
            ]
        return data

    @classmethod
    def get_overview(cls) -> dict:
        cls.report_core_api()
        services = ServiceHeartbeatService.list_service_groups(cls.SERVICE_NAMES)
        queues = QueueStatsService.get_stats()
        recent_errors, recent_error_count = RecentErrorsService.paginate_errors(
            1,
            RecentErrorsService.DEFAULT_LIMIT,
        )
        diagnostics = DiagnosticsService.list_diagnostics(queues)
        api_worker_count = cls.online_instance_count(services, RuntimeServiceName.API_WORKER)
        api_worker_desired_count = SystemConfigService.get_ranged_int(API_WORKER_DESIRED_COUNT_KEY)
        diagnostics = cls.with_api_worker_capacity_diagnostic(
            diagnostics, api_worker_count, api_worker_desired_count,
        )
        thread_pool_size = SystemConfigService.get_api_worker_thread_pool_size()
        api_total_concurrency = max(1, api_worker_count or 1) * thread_pool_size
        healthy_service_count = len([item for item in services if item['status'] == 'online'])
        total_service_count = len(cls.SERVICE_NAMES)
        return {
            'summary': {
                'healthy_service_count': healthy_service_count,
                'total_service_count': total_service_count,
                'api_worker_count': api_worker_count,
                'api_worker_desired_count': api_worker_desired_count,
                'api_worker_thread_pool_size': thread_pool_size,
                'api_total_concurrency': api_total_concurrency,
                'pending_task_count': QueueStatsService.pending_total(queues),
                'recent_error_count': recent_error_count,
            },
            'services': services,
            'queues': queues,
            'recent_errors': recent_errors,
            'diagnostics': diagnostics,
        }

    @classmethod
    async def aget_overview(cls) -> dict:
        await cls.areport_core_api()
        services = await ServiceHeartbeatService.alist_service_groups(cls.SERVICE_NAMES)
        queues = await QueueStatsService.aget_stats()
        recent_errors, recent_error_count = await RecentErrorsService.apaginate_errors(
            1,
            RecentErrorsService.DEFAULT_LIMIT,
        )
        diagnostics = await DiagnosticsService.alist_diagnostics(queues)
        api_worker_count = cls.online_instance_count(services, RuntimeServiceName.API_WORKER)
        api_worker_desired_count = int(
            await SystemConfigService.aget(
                API_WORKER_DESIRED_COUNT_KEY,
                default=API_WORKER_DESIRED_COUNT_DEFAULT,
            )
            or API_WORKER_DESIRED_COUNT_DEFAULT
        )
        diagnostics = cls.with_api_worker_capacity_diagnostic(
            diagnostics, api_worker_count, api_worker_desired_count,
        )
        thread_pool_size = await SystemConfigService.aget_api_worker_thread_pool_size()
        api_total_concurrency = max(1, api_worker_count or 1) * thread_pool_size
        healthy_service_count = len([item for item in services if item['status'] == 'online'])
        total_service_count = len(cls.SERVICE_NAMES)
        return {
            'summary': {
                'healthy_service_count': healthy_service_count,
                'total_service_count': total_service_count,
                'api_worker_count': api_worker_count,
                'api_worker_desired_count': api_worker_desired_count,
                'api_worker_thread_pool_size': thread_pool_size,
                'api_total_concurrency': api_total_concurrency,
                'pending_task_count': QueueStatsService.pending_total(queues),
                'recent_error_count': recent_error_count,
            },
            'services': services,
            'queues': queues,
            'recent_errors': recent_errors,
            'diagnostics': diagnostics,
        }

    @classmethod
    def report_core_api(cls):
        instance_name = os.getenv('SERVICE_INSTANCE_NAME') or socket.gethostname()
        ServiceHeartbeatService.beat(
            RuntimeServiceName.CORE_API,
            instance_name=instance_name,
            metadata={
                'mode': 'request-observed',
                'version': os.getenv('APP_VERSION') or os.getenv('DJANGO_ENV'),
            },
        )

    @classmethod
    async def areport_core_api(cls):
        instance_name = os.getenv('SERVICE_INSTANCE_NAME') or socket.gethostname()
        await ServiceHeartbeatService.abeat(
            RuntimeServiceName.CORE_API,
            instance_name=instance_name,
            metadata={
                'mode': 'request-observed',
                'version': os.getenv('APP_VERSION') or os.getenv('DJANGO_ENV'),
            },
        )

    @staticmethod
    def online_instance_count(services: list[dict], service_name: str) -> int:
        service = next((item for item in services if item['service_name'] == service_name), None)
        return service['online_count'] if service else 0

    @staticmethod
    def with_api_worker_capacity_diagnostic(
            diagnostics: list[dict], online_count: int, desired_count: int,
    ) -> list[dict]:
        if online_count == desired_count:
            return diagnostics
        return [
            *diagnostics,
            {
                'key': 'api_worker_desired_count',
                'title': 'API Worker 实例数',
                'status': 'warning',
                'status_name': '需关注',
                'message': f'当前在线 {online_count} 个，期望 {desired_count} 个',
                'suggestion': '请通过部署控制器调整 API Worker StatefulSet 副本数',
            },
        ]
