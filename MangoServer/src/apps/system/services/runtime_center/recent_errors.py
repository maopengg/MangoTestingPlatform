from datetime import datetime, timezone as datetime_timezone

from django.db.models import Q
from django.utils import timezone

from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.user.services.authorization.permission import PermissionMenuService


class RecentErrorsService:
    DEFAULT_LIMIT = 20

    @staticmethod
    def visible_rows(rows: list[dict], user) -> list[dict]:
        permissions = PermissionMenuService.permission_keys_for_user(user) if user else set()
        if 'system.error_record' not in permissions:
            return []
        if 'system.error_record:read' in permissions:
            return rows
        list_fields = {
            'time', 'source', 'event_source', 'source_name', 'object_id', 'title', 'message',
            'exception_type', 'status', 'status_name', 'count',
        }
        return [{key: value for key, value in row.items() if key in list_fields} for row in rows]

    @classmethod
    def list_errors(cls, limit: int = DEFAULT_LIMIT) -> list[dict]:
        return cls.paginate_errors(1, limit)[0]

    @classmethod
    async def alist_errors(cls, limit: int = DEFAULT_LIMIT) -> list[dict]:
        return (await cls.apaginate_errors(1, limit))[0]

    @classmethod
    def paginate_errors(
            cls,
            page: int,
            page_size: int,
            category: str | None = None,
            keyword: str | None = None,
            source: str | None = None,
    ) -> tuple[list[dict], int]:
        page = max(int(page), 1)
        page_size = max(int(page_size), 1)
        end = page * page_size
        items = []
        keyword = (keyword or '').strip()
        source = (source or '').strip()
        system_sources = [item.strip() for item in source.split(',') if item.strip()]
        include_system = category in (None, '', 'system_error_event') and source != 'schedule_fire'
        include_schedule = category in (None, '', 'schedule_fire') and source in ('', 'schedule_fire')
        if include_system:
            items.extend(cls.system_errors(end, keyword, system_sources))
        if include_schedule:
            items.extend(cls.schedule_fire_errors(end, keyword))
        total = (
                (cls.system_error_count(keyword, system_sources) if include_system else 0)
                + (cls.schedule_fire_error_count(keyword) if include_schedule else 0)
        )
        empty_time = datetime.min.replace(tzinfo=datetime_timezone.utc)
        items.sort(key=lambda item: item.get('sort_time') or empty_time, reverse=True)
        start = (page - 1) * page_size
        rows = items[start:end]
        return cls.clean_sort_time(rows), total

    @classmethod
    async def apaginate_errors(cls, page: int, page_size: int) -> tuple[list[dict], int]:
        page = max(int(page), 1)
        page_size = max(int(page_size), 1)
        end = page * page_size
        items = []
        items.extend(await SystemErrorEventService.alist_recent(end))
        items.extend(await cls.aschedule_fire_errors(end))
        total = await SystemErrorEventService.acount() + await cls.aschedule_fire_error_count()
        empty_time = datetime.min.replace(tzinfo=datetime_timezone.utc)
        items.sort(key=lambda item: item.get('sort_time') or empty_time, reverse=True)
        start = (page - 1) * page_size
        return cls.clean_sort_time(items[start:end]), total

    @staticmethod
    def clean_sort_time(items: list[dict]) -> list[dict]:
        return [{key: value for key, value in item.items() if key != 'sort_time'} for item in items]

    @staticmethod
    def system_errors(limit: int, keyword: str = '', sources: list[str] | None = None) -> list[dict]:
        queryset = SystemErrorEventService.queryset(keyword, sources).order_by('-last_seen_at', '-id')[:limit]
        return [SystemErrorEventService.serialize(item) for item in queryset]

    @staticmethod
    def system_error_count(keyword: str = '', sources: list[str] | None = None) -> int:
        return SystemErrorEventService.queryset(keyword, sources).count()

    @staticmethod
    def schedule_fire_error_queryset():
        # 测试套执行失败属于业务结果，已在触发记录和测试报告中呈现。
        # 系统异常页仅保留系统任务、清理、Token 刷新等调度基础设施失败。
        return ScheduleFire.objects.filter(
            status=ScheduleFireStatusEnum.FAIL.value,
        ).exclude(
            source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
        )

    @classmethod
    def schedule_fire_error_count(cls, keyword: str = '') -> int:
        queryset = cls.schedule_fire_error_queryset()
        if keyword:
            queryset = queryset.filter(Q(task_name__icontains=keyword) | Q(error_message__icontains=keyword))
        return queryset.count()

    @classmethod
    async def aschedule_fire_error_count(cls) -> int:
        return await cls.schedule_fire_error_queryset().acount()

    @classmethod
    def schedule_fire_errors(cls, limit: int, keyword: str = '') -> list[dict]:
        result = []
        queryset = cls.schedule_fire_error_queryset()
        if keyword:
            queryset = queryset.filter(Q(task_name__icontains=keyword) | Q(error_message__icontains=keyword))
        queryset = queryset.order_by('-update_time', '-id')[:limit]
        for item in queryset:
            result.append({
                'time': cls.format_time(item.update_time),
                'sort_time': cls.ensure_aware(item.update_time),
                'source': 'schedule_fire',
                'event_source': 'schedule_fire',
                'source_name': '调度异常',
                'object_id': item.id,
                'title': item.task_name or f'触发记录 {item.id}',
                'message': item.error_message or '触发执行失败',
                'status': item.status,
                'status_name': item.get_status_display(),
                'link': '/timing/fire-record/index',
                'log_query': f'schedule_fire_id="{item.id}" OR fire_id="{item.id}"',
            })
        return result

    @classmethod
    async def aschedule_fire_errors(cls, limit: int) -> list[dict]:
        result = []
        queryset = cls.schedule_fire_error_queryset().order_by('-update_time', '-id')[:limit]
        async for item in queryset:
            result.append({
                'time': cls.format_time(item.update_time),
                'sort_time': cls.ensure_aware(item.update_time),
                'source': 'schedule_fire',
                'event_source': 'schedule_fire',
                'source_name': '调度异常',
                'object_id': item.id,
                'title': item.task_name or f'触发记录 {item.id}',
                'message': item.error_message or '触发执行失败',
                'status': item.status,
                'status_name': item.get_status_display(),
                'link': '/timing/fire-record/index',
                'log_query': f'schedule_fire_id="{item.id}" OR fire_id="{item.id}"',
            })
        return result

    @staticmethod
    def format_time(value):
        value = RecentErrorsService.ensure_aware(value)
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S') if value else None

    @staticmethod
    def ensure_aware(value):
        if value and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return value
