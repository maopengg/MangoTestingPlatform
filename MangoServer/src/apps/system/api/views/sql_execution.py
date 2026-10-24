from datetime import datetime, time

from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.system.api.serializers.sql_execution import SqlExecutionRecordSerializer
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0003


class SqlExecutionRecordViews(ViewSet):
    action_permission_map = {
        'list_items': 'system.sql_execution',
        'options': 'system.sql_execution',
    }

    @staticmethod
    def _user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @classmethod
    def _visible_queryset(cls, request: Request):
        queryset = SqlExecutionRecord.objects.select_related(
            'project_product', 'datasource_alias', 'database',
        )
        user = cls._user(request)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return queryset
        if ProjectProductScopeService.can_view_all_project_data(user):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(project_product_id__in=allowed_ids)

    @staticmethod
    def _parse_datetime(value: str | None, *, end_of_day: bool = False):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            parsed_date = parse_date(value)
            if parsed_date is None:
                return None
            parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)
        if settings.USE_TZ and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    @classmethod
    def _apply_filters(cls, request: Request, queryset):
        id_values = [
            item.strip()
            for value in request.query_params.getlist('id__in')
            for item in str(value).split(',')
            if item.strip()
        ]
        if 'id__in' in request.query_params and not id_values:
            return None
        if id_values:
            if any(not value.isascii() or not value.isdigit() or int(value) <= 0 for value in id_values):
                return None
            queryset = queryset.filter(id__in=[int(value) for value in id_values])
        integer_filters = ('id', 'source_id', 'project_product_id', 'test_env', 'datasource_alias_id')
        for key in integer_filters:
            value = request.query_params.get(key)
            if value in (None, ''):
                continue
            if not str(value).isdigit():
                return None
            queryset = queryset.filter(**{key: int(value)})

        for key in ('source_type', 'source_stage', 'status'):
            value = str(request.query_params.get(key) or '').strip()
            if value:
                queryset = queryset.filter(**{key: value})

        is_slow = request.query_params.get('is_slow')
        if is_slow not in (None, ''):
            if str(is_slow).lower() not in {'true', 'false', '1', '0'}:
                return None
            queryset = queryset.filter(is_slow=str(is_slow).lower() in {'true', '1'})

        for query_key, lookup in (
                ('duration_min', 'duration_ms__gte'),
                ('duration_max', 'duration_ms__lte'),
        ):
            value = request.query_params.get(query_key)
            if value in (None, ''):
                continue
            try:
                duration = float(value)
            except (TypeError, ValueError):
                return None
            if duration < 0:
                return None
            queryset = queryset.filter(**{lookup: duration})

        sql_keyword = str(request.query_params.get('sql_keyword') or '').strip()
        if sql_keyword:
            queryset = queryset.filter(sql_text__icontains=sql_keyword[:200])

        start = cls._parse_datetime(request.query_params.get('create_time_start'))
        end = cls._parse_datetime(request.query_params.get('create_time_end'), end_of_day=True)
        if request.query_params.get('create_time_start') and start is None:
            return None
        if request.query_params.get('create_time_end') and end is None:
            return None
        if start and end and start > end:
            return None
        if start:
            queryset = queryset.filter(create_time__gte=start)
        if end:
            queryset = queryset.filter(create_time__lte=end)
        return queryset

    @action(methods=['get'], detail=False)
    @error_response('system')
    def list_items(self, request: Request):
        queryset = self._apply_filters(request, self._visible_queryset(request))
        if queryset is None:
            return ResponseData.fail(RESPONSE_MSG_0003)
        try:
            page = max(int(request.query_params.get('page') or 1), 1)
            page_size = min(max(int(request.query_params.get('pageSize') or 20), 1), 200)
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0003)
        paginator = Paginator(queryset.order_by('-create_time', '-id'), page_size)
        rows = paginator.get_page(page).object_list
        return ResponseData.success(
            RESPONSE_MSG_0001,
            SqlExecutionRecordSerializer(rows, many=True).data,
            paginator.count,
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def options(self, request: Request):
        queryset = self._visible_queryset(request)
        source_types = list(
            queryset.exclude(source_type='').values_list('source_type', flat=True).distinct().order_by('source_type')
        )
        source_stages = list(
            queryset.exclude(source_stage='').values_list('source_stage', flat=True).distinct().order_by('source_stage')
        )
        aliases = {
            row['datasource_alias_id']: row['datasource_alias__name']
            for row in queryset.values('datasource_alias_id', 'datasource_alias__name').distinct()
        }
        products = {
            row['project_product_id']: row['project_product__name']
            for row in queryset.values('project_product_id', 'project_product__name').distinct()
        }
        return ResponseData.success(RESPONSE_MSG_0001, {
            'source_type_options': [{'key': value, 'title': value} for value in source_types],
            'source_stage_options': [{'key': value, 'title': value} for value in source_stages],
            'status_options': [
                {'key': 'running', 'title': '执行中'},
                {'key': 'success', 'title': '成功'},
                {'key': 'fail', 'title': '失败'},
                {'key': 'timeout', 'title': '超时'},
            ],
            'slow_options': [
                {'key': True, 'title': '慢SQL'},
                {'key': False, 'title': '正常'},
            ],
            'environment_options': [
                {'key': key, 'title': title} for key, title in EnvironmentEnum.obj().items()
            ],
            'datasource_alias_options': [
                {'key': key, 'title': title} for key, title in sorted(aliases.items())
            ],
            'project_product_options': [
                {'key': key, 'title': title} for key, title in sorted(products.items())
            ],
        })
