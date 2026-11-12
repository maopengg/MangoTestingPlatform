from django.conf import settings

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.queue_stats import QueueStatsService
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.services.scheduling.system_job import SystemJobService


class DiagnosticsService:
    PENDING_WARNING_THRESHOLD = 50
    PENDING_ERROR_THRESHOLD = 200

    @classmethod
    def list_diagnostics(cls, queues: dict | None = None) -> list[dict]:
        queues = queues or QueueStatsService.get_stats()
        diagnostics = [
            cls.service_online(
                'scheduler_online',
                'scheduler-service 在线状态',
                RuntimeServiceName.SCHEDULER,
                'scheduler-service 离线时，定时任务不会触发或分发。',
            ),
            cls.service_online(
                'api_worker_online',
                'API Worker 在线状态',
                RuntimeServiceName.API_WORKER,
                'api-worker 离线时，API 自动化任务不会被消费。',
            ),
            cls.api_worker_thread_pool_size(),
            cls.service_online(
                'mcp_service_online',
                'MCP 服务在线状态',
                RuntimeServiceName.MCP,
                'mcp-service 离线时，AI/MCP 工具调用不可用。',
            ),
            cls.service_online(
                'realtime_service_online',
                'realtime-service 在线状态',
                RuntimeServiceName.REALTIME,
                'realtime-service 离线时，执行器连接和实时消息不可用。',
            ),
            cls.service_online(
                'monitoring_service_online',
                'monitoring-service 在线状态',
                RuntimeServiceName.MONITORING,
                'monitoring-service 离线时，监控脚本不会启动、停止或恢复。',
            ),
            cls.file_storage_config(),
            cls.mcp_access_config(),
            cls.system_jobs_config(),
            cls.pending_task_backlog(queues),
        ]
        return diagnostics

    @classmethod
    async def alist_diagnostics(cls, queues: dict | None = None) -> list[dict]:
        queues = queues or await QueueStatsService.aget_stats()
        diagnostics = [
            await cls.aservice_online(
                'scheduler_online',
                'scheduler-service 在线状态',
                RuntimeServiceName.SCHEDULER,
                'scheduler-service 离线时，定时任务不会触发或分发。',
            ),
            await cls.aservice_online(
                'api_worker_online',
                'API Worker 在线状态',
                RuntimeServiceName.API_WORKER,
                'api-worker 离线时，API 自动化任务不会被消费。',
            ),
            await cls.aapi_worker_thread_pool_size(),
            await cls.aservice_online(
                'mcp_service_online',
                'MCP 服务在线状态',
                RuntimeServiceName.MCP,
                'mcp-service 离线时，AI/MCP 工具调用不可用。',
            ),
            await cls.aservice_online(
                'realtime_service_online',
                'realtime-service 在线状态',
                RuntimeServiceName.REALTIME,
                'realtime-service 离线时，执行器连接和实时消息不可用。',
            ),
            await cls.aservice_online(
                'monitoring_service_online',
                'monitoring-service 在线状态',
                RuntimeServiceName.MONITORING,
                'monitoring-service 离线时，监控脚本不会启动、停止或恢复。',
            ),
            cls.file_storage_config(),
            cls.mcp_access_config(),
            cls.system_jobs_config(),
            cls.pending_task_backlog(queues),
        ]
        return diagnostics

    @staticmethod
    def item(key: str, title: str, status: str, message: str, suggestion: str | None = None) -> dict:
        return {
            'key': key,
            'title': title,
            'status': status,
            'status_name': {
                'success': '正常',
                'warning': '警告',
                'error': '异常',
            }.get(status, '未知'),
            'message': message,
            'suggestion': suggestion,
        }

    @classmethod
    def service_online(cls, key: str, title: str, service_name: str, error_message: str) -> dict:
        count = len(ServiceHeartbeatService.get_online_instances(service_name))
        if count:
            return cls.item(key, title, 'success', f'当前在线 {count} 个实例。')
        return cls.item(key, title, 'error', error_message, '检查对应服务容器、Pod 或启动脚本日志。')

    @classmethod
    async def aservice_online(cls, key: str, title: str, service_name: str, error_message: str) -> dict:
        count = len(await ServiceHeartbeatService.aget_online_instances(service_name))
        if count:
            return cls.item(key, title, 'success', f'当前在线 {count} 个实例。')
        return cls.item(key, title, 'error', error_message, '检查对应服务容器、Pod 或启动脚本日志。')

    @classmethod
    def api_worker_thread_pool_size(cls) -> dict:
        size = SystemConfigService.get_api_worker_thread_pool_size()
        if size > 0:
            return cls.item(
                'api_worker_thread_pool_size',
                'API Worker 线程池配置',
                'success',
                f'当前线程池大小为 {size}。',
            )
        return cls.item(
            'api_worker_thread_pool_size',
            'API Worker 线程池配置',
            'error',
            'API Worker 线程池大小未正确配置。',
            '到系统设置的API自动化配置中设置线程池大小。',
        )

    @classmethod
    async def aapi_worker_thread_pool_size(cls) -> dict:
        size = await SystemConfigService.aget_api_worker_thread_pool_size()
        if size > 0:
            return cls.item(
                'api_worker_thread_pool_size',
                'API Worker 线程池配置',
                'success',
                f'当前线程池大小为 {size}。',
            )
        return cls.item(
            'api_worker_thread_pool_size',
            'API Worker 线程池配置',
            'error',
            'API Worker 线程池大小未正确配置。',
            '到系统设置的API自动化配置中设置线程池大小。',
        )

    @classmethod
    def file_storage_config(cls) -> dict:
        backend = getattr(settings, 'FILE_STORAGE_BACKEND', 'local')
        if backend == 'local':
            return cls.item('file_storage_config', '文件存储配置', 'success', '当前使用本地文件存储。')
        missing = []
        for key in ['MINIO_STORAGE_ENDPOINT', 'MINIO_STORAGE_MEDIA_BUCKET_NAME', 'MINIO_PUBLIC_BASE_URL']:
            if not getattr(settings, key, None):
                missing.append(key)
        if missing:
            return cls.item(
                'file_storage_config',
                '文件存储配置',
                'error',
                f'对象存储配置不完整：{", ".join(missing)}。',
                '检查当前环境配置文件或容器环境变量。',
            )
        return cls.item(
            'file_storage_config',
            '文件存储配置',
            'success',
            f'当前使用 {backend}，公开访问地址已配置。',
        )

    @classmethod
    def mcp_access_config(cls) -> dict:
        hosts = getattr(settings, 'MCP_ALLOWED_HOSTS', [])
        origins = getattr(settings, 'MCP_ALLOWED_ORIGINS', [])
        if hosts and origins:
            return cls.item('mcp_access_config', 'MCP 访问域名配置', 'success', 'MCP Host/Origin 白名单已配置。')
        return cls.item(
            'mcp_access_config',
            'MCP 访问域名配置',
            'warning',
            'MCP Host/Origin 白名单未完整配置。',
            '检查当前环境配置中的 MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS。',
        )

    @classmethod
    def system_jobs_config(cls) -> dict:
        job_count = len(SystemJobService.JOBS)
        if job_count:
            return cls.item('system_jobs_config', '系统定时任务初始化', 'success',
                            f'当前已定义 {job_count} 个系统定时任务。')
        return cls.item('system_jobs_config', '系统定时任务初始化', 'error', '未找到系统定时任务定义。')

    @classmethod
    def pending_task_backlog(cls, queues: dict) -> dict:
        pending_count = QueueStatsService.pending_total(queues)
        if pending_count >= cls.PENDING_ERROR_THRESHOLD:
            return cls.item(
                'pending_task_backlog',
                '任务积压',
                'error',
                f'当前待执行任务 {pending_count} 个，积压严重。',
                '检查 api-worker、scheduler-service 和执行器状态。',
            )
        if pending_count >= cls.PENDING_WARNING_THRESHOLD:
            return cls.item(
                'pending_task_backlog',
                '任务积压',
                'warning',
                f'当前待执行任务 {pending_count} 个，建议关注消费速度。',
                '检查 Worker 并发配置和业务库压力。',
            )
        return cls.item('pending_task_backlog', '任务积压', 'success', f'当前待执行任务 {pending_count} 个。')
