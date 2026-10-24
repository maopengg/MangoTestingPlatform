import hashlib
import os
import traceback as traceback_module
from datetime import timedelta

from django.db import IntegrityError
from django.db.models import F, Q
from django.utils import timezone

from src.apps.monitoring.models import SystemErrorEvent
from src.common.enums.system_error import SystemErrorEventSource
from src.common.exceptions.normalization import normalize_expected_exception
from src.common.logging import log


class SystemErrorEventService:
    DEFAULT_RETENTION_DAYS = 30
    DEFAULT_LIMIT = 10
    MESSAGE_MAX_LENGTH = 500

    SOURCE_SERVICE_MAP = {
        SystemErrorEventSource.HTTP: 'core-api',
        SystemErrorEventSource.DRF: 'core-api',
        SystemErrorEventSource.SCHEDULER: 'scheduler-service',
        SystemErrorEventSource.API_WORKER: 'api-worker',
        SystemErrorEventSource.MCP: 'mcp-service',
        SystemErrorEventSource.REALTIME: 'realtime-service',
        SystemErrorEventSource.MONITORING: 'monitoring-service',
        SystemErrorEventSource.PERFORMANCE: 'scheduler-service',
        SystemErrorEventSource.ACTUATOR: 'actuator',
        SystemErrorEventSource.FRONTEND: 'web-console',
    }

    SOURCE_NAME_MAP = {
        SystemErrorEventSource.HTTP: '接口异常',
        SystemErrorEventSource.DRF: '接口异常',
        SystemErrorEventSource.SCHEDULER: '调度服务异常',
        SystemErrorEventSource.API_WORKER: 'API Worker异常',
        SystemErrorEventSource.MCP: 'MCP服务异常',
        SystemErrorEventSource.REALTIME: '实时服务异常',
        SystemErrorEventSource.MONITORING: '监控服务异常',
        SystemErrorEventSource.PERFORMANCE: '性能任务异常',
        SystemErrorEventSource.ACTUATOR: '执行器异常',
        SystemErrorEventSource.FRONTEND: '前端异常',
    }

    @classmethod
    def record_exception(
            cls,
            error: Exception,
            source: str,
            request=None,
            request_path: str | None = None,
            service_name: str | None = None,
            trace: str | None = None,
    ):
        if normalize_expected_exception(error):
            return
        try:
            trace_text = trace or traceback_module.format_exc()
            path = cls.resolve_request_path(request, request_path)
            cls.record(
                service_name=service_name or cls.resolve_service_name(source),
                source=source,
                request_path=path,
                exception_type=error.__class__.__name__,
                message=str(error) or error.__class__.__name__,
                trace=trace_text,
            )
        except Exception as record_error:
            log.system.warning(f'系统异常事件记录失败：{record_error}')

    @classmethod
    def record(
            cls,
            service_name: str,
            source: str,
            request_path: str | None,
            exception_type: str,
            message: str,
            trace: str | None = None,
    ):
        now = timezone.now()
        normalized_message = cls.truncate(message, cls.MESSAGE_MAX_LENGTH)
        fingerprint = cls.build_fingerprint(service_name, source, request_path, exception_type, normalized_message)
        defaults = {
            'service_name': service_name,
            'source': source,
            'request_path': request_path,
            'exception_type': exception_type,
            'message': normalized_message,
            'traceback': trace,
            'last_seen_at': now,
        }
        updated = SystemErrorEvent.objects.filter(fingerprint=fingerprint).update(
            count=F('count') + 1,
            traceback=trace,
            message=normalized_message,
            last_seen_at=now,
            update_time=now,
        )
        if updated:
            return
        try:
            SystemErrorEvent.objects.create(fingerprint=fingerprint, **defaults)
        except IntegrityError:
            SystemErrorEvent.objects.filter(fingerprint=fingerprint).update(
                count=F('count') + 1,
                traceback=trace,
                message=normalized_message,
                last_seen_at=now,
                update_time=now,
            )

    @classmethod
    def list_recent(cls, limit: int = DEFAULT_LIMIT) -> list[dict]:
        queryset = SystemErrorEvent.objects.order_by('-last_seen_at', '-id')[:limit]
        return [cls.serialize(item) for item in queryset]

    @staticmethod
    def queryset(keyword: str = '', sources: list[str] | None = None):
        queryset = SystemErrorEvent.objects.all()
        if sources:
            queryset = queryset.filter(source__in=sources)
        if keyword:
            queryset = queryset.filter(
                Q(request_path__icontains=keyword)
                | Q(service_name__icontains=keyword)
                | Q(exception_type__icontains=keyword)
                | Q(message__icontains=keyword)
            )
        return queryset

    @classmethod
    def count(cls) -> int:
        return SystemErrorEvent.objects.count()

    @classmethod
    async def alist_recent(cls, limit: int = DEFAULT_LIMIT) -> list[dict]:
        queryset = SystemErrorEvent.objects.order_by('-last_seen_at', '-id')[:limit]
        return [cls.serialize(item) async for item in queryset]

    @classmethod
    async def acount(cls) -> int:
        return await SystemErrorEvent.objects.acount()

    @classmethod
    def cleanup_expired(cls, days: int | None = None) -> int:
        retention_days = days or cls.DEFAULT_RETENTION_DAYS
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        return SystemErrorEvent.objects.filter(last_seen_at__lt=cutoff_time).delete()[0]

    @classmethod
    def serialize(cls, item: SystemErrorEvent) -> dict:
        return {
            'time': cls.format_time(item.last_seen_at),
            'sort_time': cls.ensure_aware(item.last_seen_at),
            'source': 'system_error_event',
            'event_source': item.source,
            'source_name': cls.SOURCE_NAME_MAP.get(item.source, item.source),
            'object_id': item.id,
            'title': item.request_path or item.service_name,
            'message': item.message,
            'service_name': item.service_name,
            'exception_type': item.exception_type,
            'traceback': item.traceback,
            'status': 'error',
            'status_name': '异常',
            'count': item.count,
            'link': None,
            'log_query': f'service="{item.service_name}" AND fingerprint="{item.fingerprint}"',
        }

    @classmethod
    def resolve_service_name(cls, source: str) -> str:
        return os.getenv('SERVICE_NAME') or os.getenv('APP_SERVICE_NAME') or cls.SOURCE_SERVICE_MAP.get(source,
                                                                                                        'core-api')

    @staticmethod
    def resolve_request_path(request, request_path: str | None):
        if request_path:
            return request_path[:255]
        if not request:
            return None
        method = getattr(request, 'method', None)
        path = getattr(request, 'path', None) or getattr(request, 'path_info', None)
        if method and path:
            return f'{method} {path}'[:255]
        return str(path)[:255] if path else None

    @staticmethod
    def build_fingerprint(
            service_name: str,
            source: str,
            request_path: str | None,
            exception_type: str,
            message: str,
    ) -> str:
        raw = '|'.join([service_name or '', source or '', request_path or '', exception_type or '', message or ''])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def truncate(value: str | None, length: int) -> str:
        text = value or ''
        return text[:length]

    @staticmethod
    def format_time(value):
        value = SystemErrorEventService.ensure_aware(value)
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S') if value else None

    @staticmethod
    def ensure_aware(value):
        if value and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return value


def record_system_error(error: Exception, source: str, **kwargs):
    """供 Django ``import_string`` 加载的稳定模块级入口。"""
    return SystemErrorEventService.record_exception(error, source, **kwargs)
