import os
import socket
from datetime import timedelta

from django.utils import timezone

from src.apps.monitoring.models import ServiceHeartbeat
from src.common.decorators.retry import async_task_db_connection
from src.common.logging import log


class ServiceHeartbeatService:
    ONLINE_SECONDS = 60
    STALE_SECONDS = 180
    CLEANUP_RETENTION_DAYS = 7

    @classmethod
    @async_task_db_connection(max_retries=1, retry_delay=1)
    def beat(
            cls,
            service_name: str,
            instance_name: str | None = None,
            metadata: dict | None = None,
            status: int = 1,
    ):
        now = timezone.now()
        instance = instance_name or socket.gethostname()
        defaults = {
            'host_name': socket.gethostname(),
            'pod_name': os.getenv('POD_NAME') or os.getenv('HOSTNAME'),
            'process_id': os.getpid(),
            'status': status,
            'last_seen_at': now,
            'metadata': metadata or {},
        }
        try:
            ServiceHeartbeat.objects.update_or_create(
                service_name=service_name,
                instance_name=instance,
                defaults=defaults,
            )
        except Exception as error:
            log.system.warning(
                f'服务心跳写入失败：service={service_name}, instance={instance}, error={error}'
            )

    @classmethod
    async def abeat(
            cls,
            service_name: str,
            instance_name: str | None = None,
            metadata: dict | None = None,
            status: int = 1,
    ):
        now = timezone.now()
        instance = instance_name or socket.gethostname()
        defaults = {
            'host_name': socket.gethostname(),
            'pod_name': os.getenv('POD_NAME') or os.getenv('HOSTNAME'),
            'process_id': os.getpid(),
            'status': status,
            'last_seen_at': now,
            'metadata': metadata or {},
        }
        try:
            await ServiceHeartbeat.objects.aupdate_or_create(
                service_name=service_name,
                instance_name=instance,
                defaults=defaults,
            )
        except Exception as error:
            log.system.warning(
                f'服务心跳写入失败：service={service_name}, instance={instance}, error={error}'
            )

    @classmethod
    def beat_if_due(
            cls,
            owner,
            service_name: str,
            instance_name: str | None = None,
            metadata: dict | None = None,
            interval_seconds: int = 15,
    ):
        now = timezone.now()
        last_beat_at = getattr(owner, '_last_heartbeat_at', None)
        if last_beat_at and (now - last_beat_at).total_seconds() < interval_seconds:
            return
        setattr(owner, '_last_heartbeat_at', now)
        cls.beat(service_name, instance_name, metadata)

    @classmethod
    def list_services(cls) -> list[dict]:
        cls.mark_expired_offline()
        now = timezone.now()
        queryset = ServiceHeartbeat.objects.all().order_by('service_name', 'instance_name')
        return [cls.serialize(item, now) for item in queryset]

    @classmethod
    def list_service_groups(cls, service_names: list[str] | None = None) -> list[dict]:
        cls.mark_expired_offline(service_names)
        now = timezone.now()
        query_service_names = service_names or list(
            ServiceHeartbeat.objects.values_list('service_name', flat=True).distinct()
        )
        heartbeats = list(
            ServiceHeartbeat.objects.filter(service_name__in=query_service_names).order_by('service_name',
                                                                                           '-last_seen_at')
        )
        grouped = {service_name: [] for service_name in query_service_names}
        for heartbeat in heartbeats:
            grouped.setdefault(heartbeat.service_name, []).append(cls.serialize(heartbeat, now))
        return [cls.serialize_service_group(service_name, grouped.get(service_name, [])) for service_name in
                query_service_names]

    @classmethod
    async def alist_service_groups(cls, service_names: list[str] | None = None) -> list[dict]:
        await cls.amark_expired_offline(service_names)
        now = timezone.now()
        if service_names:
            query_service_names = service_names
        else:
            query_service_names = [
                service_name
                async for service_name in ServiceHeartbeat.objects.values_list('service_name', flat=True).distinct()
            ]
        queryset = ServiceHeartbeat.objects.filter(
            service_name__in=query_service_names
        ).order_by('service_name', '-last_seen_at')
        grouped = {service_name: [] for service_name in query_service_names}
        async for heartbeat in queryset:
            grouped.setdefault(heartbeat.service_name, []).append(cls.serialize(heartbeat, now))
        return [cls.serialize_service_group(service_name, grouped.get(service_name, [])) for service_name in
                query_service_names]

    @classmethod
    def get_online_instances(cls, service_name: str) -> list[ServiceHeartbeat]:
        cutoff_time = timezone.now() - timedelta(seconds=cls.ONLINE_SECONDS)
        return list(ServiceHeartbeat.objects.filter(
            service_name=service_name,
            status=1,
            last_seen_at__gte=cutoff_time,
        ).order_by('instance_name'))

    @classmethod
    def count_online_instances(cls, service_name: str) -> int:
        cutoff_time = timezone.now() - timedelta(seconds=cls.ONLINE_SECONDS)
        return ServiceHeartbeat.objects.filter(
            service_name=service_name,
            status=1,
            last_seen_at__gte=cutoff_time,
        ).count()

    @classmethod
    async def aget_online_instances(cls, service_name: str) -> list[ServiceHeartbeat]:
        cutoff_time = timezone.now() - timedelta(seconds=cls.ONLINE_SECONDS)
        queryset = ServiceHeartbeat.objects.filter(
            service_name=service_name,
            status=1,
            last_seen_at__gte=cutoff_time,
        ).order_by('instance_name')
        return [item async for item in queryset]

    @classmethod
    def serialize_service_group(cls, service_name: str, instances: list[dict]) -> dict:
        online_instances = [item for item in instances if item['status'] == 'online']
        stale_instances = [item for item in instances if item['status'] == 'stale']
        current_instances = online_instances
        if online_instances:
            status = 'online'
        elif stale_instances:
            status = 'stale'
            current_instances = stale_instances
        else:
            status = 'offline'
        latest_instance = instances[0] if instances else {}
        metadata_source = current_instances[0] if current_instances else latest_instance
        return {
            'id': service_name,
            'service_name': service_name,
            'status': status,
            'status_name': cls.service_group_status_name(status),
            'last_seen_at': latest_instance.get('last_seen_at'),
            'online_count': len(online_instances),
            'stale_count': len(stale_instances),
            'instance_count': len(current_instances),
            'instances': current_instances,
            'metadata': metadata_source.get('metadata') or {},
            'log_query': f'service="{service_name}"',
        }

    @classmethod
    def serialize(cls, heartbeat: ServiceHeartbeat, now=None) -> dict:
        now = cls.ensure_aware(now or timezone.now())
        last_seen_at = cls.ensure_aware(heartbeat.last_seen_at) if heartbeat.last_seen_at else None
        age_seconds = int((now - last_seen_at).total_seconds()) if last_seen_at else None
        runtime_status = cls.runtime_status(age_seconds, heartbeat.status)
        return {
            'id': heartbeat.id,
            'service_name': heartbeat.service_name,
            'instance_name': heartbeat.instance_name,
            'host_name': heartbeat.host_name,
            'pod_name': heartbeat.pod_name,
            'process_id': heartbeat.process_id,
            'status': runtime_status,
            'status_name': cls.runtime_status_name(runtime_status),
            'raw_status': heartbeat.status,
            'last_seen_at': cls.format_time(last_seen_at),
            'age_seconds': age_seconds,
            'metadata': heartbeat.metadata or {},
            'log_query': f'service="{heartbeat.service_name}" AND instance="{heartbeat.instance_name}"',
        }

    @classmethod
    def runtime_status(cls, age_seconds: int | None, raw_status: int) -> str:
        if raw_status == 0:
            return 'offline'
        if raw_status != 1:
            return 'error'
        if age_seconds is None:
            return 'offline'
        if age_seconds <= cls.ONLINE_SECONDS:
            return 'online'
        if age_seconds <= cls.STALE_SECONDS:
            return 'stale'
        return 'offline'

    @staticmethod
    def runtime_status_name(status: str) -> str:
        return {
            'online': '在线',
            'stale': '心跳延迟',
            'offline': '离线',
            'error': '异常',
        }.get(status, '未知')

    @staticmethod
    def service_group_status_name(status: str) -> str:
        return {
            'online': '正常',
            'stale': '心跳延迟',
            'offline': '离线',
            'error': '异常',
        }.get(status, '未知')

    @staticmethod
    def ensure_aware(value):
        if value and timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value

    @classmethod
    def format_time(cls, value):
        return timezone.localtime(cls.ensure_aware(value)).strftime('%Y-%m-%d %H:%M:%S') if value else None

    @classmethod
    @async_task_db_connection()
    def cleanup_expired(cls, days: int | None = None) -> int:
        retention_days = days or cls.CLEANUP_RETENTION_DAYS
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        return ServiceHeartbeat.objects.filter(last_seen_at__lt=cutoff_time).delete()[0]

    @classmethod
    def mark_expired_offline(cls, service_names: list[str] | None = None) -> int:
        cutoff_time = timezone.now() - timedelta(seconds=cls.STALE_SECONDS)
        queryset = ServiceHeartbeat.objects.filter(status=1, last_seen_at__lt=cutoff_time)
        if service_names:
            queryset = queryset.filter(service_name__in=service_names)
        return queryset.update(status=0)

    @classmethod
    async def amark_expired_offline(cls, service_names: list[str] | None = None) -> int:
        cutoff_time = timezone.now() - timedelta(seconds=cls.STALE_SECONDS)
        queryset = ServiceHeartbeat.objects.filter(status=1, last_seen_at__lt=cutoff_time)
        if service_names:
            queryset = queryset.filter(service_name__in=service_names)
        return await queryset.aupdate(status=0)
