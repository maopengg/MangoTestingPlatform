from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from hashlib import sha256

from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.test_center.models import TestSuite
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.responses.model_crud import get_request_project_id, get_request_project_product_id


class TestSuiteReportOverviewService:
    """Build report-list charts with the same filters and data scope as the list."""

    WEEK_COUNT = 12
    CACHE_PREFIX = 'system:test-suite:report-overview:v1'
    COMPLETED_STATUSES = (
        TaskEnum.FAIL.value,
        TaskEnum.SUCCESS.value,
        TaskEnum.WARNING.value,
        TaskEnum.STOPPED.value,
    )

    @classmethod
    def overview(cls, request) -> dict:
        cache_key = cls._cache_key(request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        data = cls._build_overview(request)
        cache.set(cache_key, data, SystemConfigService.get_ranged_int('REPORT_OVERVIEW_CACHE_SECONDS'))
        return data

    @classmethod
    def _build_overview(cls, request) -> dict:
        queryset = cls._filtered_queryset(request)
        distribution_map = {
            row['status']: row['value']
            for row in queryset.values('status').annotate(value=Count('id'))
        }
        distribution = [
            {
                'status': status,
                'name': TaskEnum.get_value(status),
                'value': distribution_map.get(status, 0),
            }
            for status in (
                TaskEnum.SUCCESS.value,
                TaskEnum.FAIL.value,
                TaskEnum.WARNING.value,
                TaskEnum.PROCEED.value,
                TaskEnum.STAY_BEGIN.value,
                TaskEnum.STOPPED.value,
            )
        ]
        trend = cls._weekly_trend(queryset)
        return {
            'total': sum(item['value'] for item in distribution),
            'status_distribution': distribution,
            'source_distribution': {
                'batch': queryset.filter(tasks__isnull=True).count(),
                'scheduled': queryset.filter(tasks__isnull=False).count(),
            },
            'trend': trend,
            # Temporary compatibility for clients using the former payload.
            'successSun': distribution_map.get(TaskEnum.SUCCESS.value, 0),
            'failSun': distribution_map.get(TaskEnum.FAIL.value, 0),
            'success': [item['success_count'] for item in trend],
            'fail': [item['fail_count'] for item in trend],
        }

    @classmethod
    def _cache_key(cls, request) -> str:
        query_params = request.query_params
        headers = getattr(request, 'headers', {})
        if hasattr(query_params, 'lists'):
            filters = {
                key: [str(value) for value in values]
                for key, values in query_params.lists()
            }
        else:
            filters = {
                str(key): value if isinstance(value, list) else str(value)
                for key, value in query_params.items()
            }
        payload = json.dumps(
            {
                'filters': filters,
                'project_id': headers.get('X-Project-Id'),
                'project_product_id': headers.get('X-Project-Product-Id'),
                'permission_scope': cls._permission_scope(request),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        return f'{cls.CACHE_PREFIX}:{sha256(payload.encode("utf-8")).hexdigest()[:32]}'

    @staticmethod
    def _permission_scope(request) -> str:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None:
            return 'anonymous'
        user_id = getattr(user, 'id', 'unknown')
        if (
                PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return f'user:{user_id}:all'
        allowed_ids = sorted(ProjectProductScopeService.project_product_ids_for_user(user))
        return f"user:{user_id}:products:{','.join(map(str, allowed_ids))}"

    @classmethod
    def _filtered_queryset(cls, request):
        params = request.query_params
        queryset = TestSuite.objects.filter(report_retained=True)
        case_types = [value.strip() for value in str(params.get('case_type__in') or '').split(',') if value.strip()]
        if case_types:
            if not all(value.isdigit() for value in case_types):
                return queryset.none()
            queryset = queryset.filter(testsuitedetails__type__in=case_types).distinct()
        exact_filters = {
            'id': params.get('id'),
            'project_product_id': params.get('project_product'),
            'module_id': params.get('module'),
            'status': params.get('status'),
            'tasks_id': params.get('tasks_id'),
            'user_id': params.get('user'),
            'test_env': params.get('test_env'),
            'execution_scope': params.get('execution_scope'),
            'create_time__gte': params.get('create_time__gte'),
            'create_time__lte': params.get('create_time__lte'),
        }
        for field, value in exact_filters.items():
            if value not in (None, ''):
                queryset = queryset.filter(**{field: value})

        for query_key, field in {
            'status__in': 'status__in',
            'user__in': 'user_id__in',
            'test_env__in': 'test_env__in',
            'execution_scope__in': 'execution_scope__in',
        }.items():
            values = [
                item.strip()
                for item in str(params.get(query_key) or '').split(',')
                if item.strip()
            ]
            if values:
                queryset = queryset.filter(**{field: values})

        scene_values = [
            item.strip()
            for value in [params.get('execution_scene'), params.get('execution_scene__in')]
            for item in str(value or '').split(',')
            if item.strip()
        ]
        if scene_values:
            scene_query = Q()
            for scene in dict.fromkeys(scene_values):
                scene_query |= Q(execution_scenes__contains=[scene])
            queryset = queryset.filter(scene_query)

        tasks_isnull = str(params.get('tasks__isnull') or '').strip().lower()
        if tasks_isnull in {'true', 'false'}:
            queryset = queryset.filter(tasks__isnull=tasks_isnull == 'true')

        module_ids = [
            value.strip()
            for value in str(params.get('module__in') or '').split(',')
            if value.strip()
        ]
        if module_ids:
            queryset = queryset.filter(module_id__in=module_ids)

        if params.get('project_product') in (None, ''):
            project_product_id = get_request_project_product_id(request)
            project_id = get_request_project_id(request)
            if project_product_id:
                queryset = queryset.filter(project_product_id=project_product_id)
            elif project_id:
                queryset = queryset.filter(project_product__project_id=project_id)

        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is not None
                and not PermissionMenuService.is_effective_super_admin(user)
                and not ProjectProductScopeService.can_view_all_project_data(user)
        ):
            allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
            queryset = queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()
        return queryset

    @classmethod
    def _weekly_trend(cls, queryset) -> list[dict]:
        now = timezone.now()
        today = timezone.localtime(now).date() if timezone.is_aware(now) else now.date()
        current_week = today - timedelta(days=today.weekday())
        first_week = current_week - timedelta(weeks=cls.WEEK_COUNT - 1)
        end_week = current_week + timedelta(weeks=1)
        first_at = datetime.combine(first_week, time.min)
        end_at = datetime.combine(end_week, time.min)
        if timezone.is_aware(now):
            first_at = timezone.make_aware(first_at, timezone.get_current_timezone())
            end_at = timezone.make_aware(end_at, timezone.get_current_timezone())
        rows = queryset.filter(
            create_time__gte=first_at,
            create_time__lt=end_at,
        ).annotate(week=TruncWeek('create_time')).values('week').annotate(
            total=Count('id'),
            batch_count=Count('id', filter=Q(tasks__isnull=True)),
            scheduled_count=Count('id', filter=Q(tasks__isnull=False)),
            success_count=Count('id', filter=Q(status=TaskEnum.SUCCESS.value)),
            fail_count=Count('id', filter=Q(status=TaskEnum.FAIL.value)),
            warning_count=Count('id', filter=Q(status=TaskEnum.WARNING.value)),
            completed_count=Count('id', filter=Q(status__in=cls.COMPLETED_STATUSES)),
        ).order_by('week')
        rows_by_week = {
            row['week'].date() if hasattr(row['week'], 'date') else row['week']: row
            for row in rows
        }

        result = []
        for offset in range(cls.WEEK_COUNT):
            week_start = first_week + timedelta(weeks=offset)
            week_end = week_start + timedelta(days=6)
            row = rows_by_week.get(week_start, {})
            completed = int(row.get('completed_count') or 0)
            success = int(row.get('success_count') or 0)
            result.append({
                'start_date': week_start.isoformat(),
                'end_date': week_end.isoformat(),
                'label': f'{week_start:%m/%d}-{week_end:%m/%d}',
                'total': int(row.get('total') or 0),
                'batch_count': int(row.get('batch_count') or 0),
                'scheduled_count': int(row.get('scheduled_count') or 0),
                'success_count': success,
                'fail_count': int(row.get('fail_count') or 0),
                'warning_count': int(row.get('warning_count') or 0),
                'pass_rate': round(success / completed * 100, 2) if completed else None,
            })
        return result
