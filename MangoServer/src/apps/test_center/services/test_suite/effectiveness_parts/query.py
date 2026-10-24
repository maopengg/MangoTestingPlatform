from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from src.apps.test_center.models import TestSuite
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService

logger = logging.getLogger(__name__)


class AutomationEffectivenessQueryMixin:
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
    def _suite_queryset(cls, request):
        start_at, end_at = cls._date_range(request)
        return cls._filtered_suite_queryset(request, start_at, end_at), start_at, end_at

    @staticmethod
    def _query_values(request, key: str) -> list[str]:
        """兼容单值、数组、重复参数及逗号分隔的多选查询参数。"""
        query_params = request.query_params
        raw_values = []
        for query_key in (key, f'{key}[]', f'{key}__in'):
            if hasattr(query_params, 'getlist'):
                raw_values.extend(query_params.getlist(query_key))
                continue
            value = query_params.get(query_key)
            if isinstance(value, (list, tuple, set)):
                raw_values.extend(value)
            elif value not in (None, ''):
                raw_values.append(value)

        values = []
        seen = set()
        for raw_value in raw_values:
            for item in str(raw_value).split(','):
                normalized = item.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    values.append(normalized)
        return values

    @classmethod
    def _filtered_suite_queryset(cls, request, start_at, end_at):
        queryset = TestSuite.objects.filter(
            tasks__isnull=False,
            create_time__gte=start_at,
            create_time__lt=end_at,
        ).select_related('tasks', 'project_product', 'module')

        filters = {
            'project_product__project_id': request.query_params.get('project_id'),
            'project_product_id': request.query_params.get('project_product_id'),
            'tasks_id': request.query_params.get('task_id'),
        }
        for key, value in filters.items():
            if value not in (None, ''):
                queryset = queryset.filter(**{key: value})

        test_envs = cls._query_values(request, 'test_env')
        if test_envs:
            queryset = queryset.filter(test_env__in=test_envs)

        execution_scopes = cls._query_values(request, 'execution_scope')
        if execution_scopes:
            queryset = queryset.filter(execution_scope__in=execution_scopes)

        execution_scenes = cls._query_values(request, 'execution_scene')
        if execution_scenes:
            scene_filter = Q()
            for execution_scene in execution_scenes:
                scene_filter |= Q(execution_scenes__contains=[execution_scene])
            queryset = queryset.filter(scene_filter)

        module_id = request.query_params.get('module_id')
        if module_id not in (None, ''):
            try:
                module_ids = ProductModuleService.module_scope_ids(int(module_id))
            except (TypeError, ValueError):
                module_ids = []
            queryset = queryset.filter(module_id__in=module_ids)

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
    def _date_range(cls, request):
        now = timezone.now()
        end_at = cls._parse_date(request.query_params.get('end_date'), end_of_day=True) or now
        start_at = cls._parse_date(request.query_params.get('start_date')) or (
                end_at - timedelta(days=cls.DEFAULT_DAYS))
        if start_at >= end_at:
            start_at = end_at - timedelta(days=cls.DEFAULT_DAYS)
        if end_at - start_at > timedelta(days=cls.MAX_DAYS):
            start_at = end_at - timedelta(days=cls.MAX_DAYS)
        return start_at, end_at

    @staticmethod
    def _previous_period(start_at: datetime, end_at: datetime) -> tuple[datetime, datetime]:
        period_length = end_at - start_at
        return start_at - period_length, start_at

    @classmethod
    def _comparison_periods(
            cls,
            start_at: datetime,
            end_at: datetime,
    ) -> tuple[
        tuple[datetime, datetime],
        tuple[datetime, datetime],
        tuple[datetime, datetime],
    ]:
        previous_period = cls._previous_period(start_at, end_at)
        two_periods_ago = cls._previous_period(*previous_period)
        three_periods_ago = cls._previous_period(*two_periods_ago)
        return previous_period, two_periods_ago, three_periods_ago

    @staticmethod
    def _parse_date(value, *, end_of_day=False):
        if not value:
            return None
        try:
            parsed = datetime.strptime(str(value), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None
        if end_of_day:
            parsed += timedelta(days=1)
        result = datetime.combine(parsed, time.min)
        if timezone.is_aware(timezone.now()):
            return timezone.make_aware(result, timezone.get_current_timezone())
        return result

    @classmethod
    def _comparison(cls, cards, previous_cards, convergence) -> dict:
        has_previous = bool(previous_cards.get('suite_count'))

        def delta(key):
            current = cards.get(key)
            previous = previous_cards.get(key)
            if not has_previous or current is None or previous is None:
                return None
            return round(current - previous, 2)

        return {
            'has_previous': has_previous,
            'final_pass_rate_delta': delta('final_pass_rate'),
            'flaky_rate_delta': delta('flaky_rate'),
            'detail_count_delta': delta('detail_count'),
            'issue_count_delta': delta('issue_count'),
            'issue_rate_delta': convergence['issue_rate_delta'],
            'previous_cards': previous_cards,
        }
