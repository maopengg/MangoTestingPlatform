from datetime import datetime, time

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
from src.apps.system.api.serializers.sql_execution import SqlExecutionRecordSerializer
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0003


class SqlExecutionRecordViews(ViewSet):

    @staticmethod
    def _user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @classmethod
    def _visible_queryset(cls, request: Request):
        return ExecutionAuditSelector.visible(cls._user(request))

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
        case_id = request.query_params.get('case_id')
        if case_id not in (None, ''):
            if not str(case_id).isascii() or not str(case_id).isdigit() or int(case_id) <= 0:
                return None
            queryset = ExecutionAuditSelector.filter_case(queryset, int(case_id))
        for key in ('case_detail_id', 'test_suite_id', 'operation'):
            value = request.query_params.get(key)
            if value in (None, ''):
                continue
            if key != 'operation':
                if not str(value).isascii() or not str(value).isdigit() or int(value) <= 0:
                    return None
                value = int(value)
            elif len(value) > 64 or not value.replace('_', '').isalnum():
                return None
            if key == 'case_detail_id':
                queryset = queryset.filter(Q(source_detail__case_detail_id=value)
                    | Q(source_detail__test_suite_detail_id=value))
            else:
                queryset = queryset.filter(**{f'source_detail__{key}': value.lower() if key == 'operation' else value})
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
        integer_filters = ('id', 'source_id', 'project_product_id', 'test_env', 'datasource_alias_id', 'datasource_type', 'database_id')
        for key in integer_filters:
            value = request.query_params.get(key)
            if value in (None, ''):
                continue
            if key == 'datasource_type' and value == 'unrecorded':
                queryset = queryset.filter(datasource_type__isnull=True)
                continue
            if not str(value).isdigit():
                return None
            queryset = queryset.filter(**{key: int(value)})

        for key in ('source_type', 'source_stage', 'status'):
            value = str(request.query_params.get(key) or '').strip()
            if value:
                queryset = queryset.filter(**{key: value})

        for key in (*integer_filters[1:], 'source_type', 'source_stage', 'status', 'is_slow'):
            if f'{key}__in' not in request.query_params:
                continue
            values = [item.strip() for raw in request.query_params.getlist(f'{key}__in')
                      for item in str(raw).split(',') if item.strip()]
            if not values:
                return None
            historical = key == 'datasource_type' and 'unrecorded' in values
            if historical:
                values = [value for value in values if value != 'unrecorded']
            if key in integer_filters:
                if any(not value.isascii() or not value.isdigit() for value in values):
                    return None
                values = [int(value) for value in values]
            if key == 'is_slow':
                if any(value.lower() not in {'true', 'false', '0', '1'} for value in values):
                    return None
                values = [value.lower() in {'true', '1'} for value in values]
            if historical:
                queryset = queryset.filter(Q(datasource_type__in=values) | Q(datasource_type__isnull=True))
            else:
                queryset = queryset.filter(**{f'{key}__in': values})

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
        """获取SQL 执行记录列表"""
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
        """获取SQL 执行记录筛选选项"""
        queryset = self._visible_queryset(request)
        source_types = list(
            queryset.exclude(source_type='').values_list('source_type', flat=True).distinct().order_by('source_type')
        )
        source_stages = list(
            queryset.exclude(source_stage='').values_list('source_stage', flat=True).distinct().order_by('source_stage')
        )
        aliases = {
            row['datasource_alias_id']: row['datasource_alias__name']
            for row in queryset.exclude(datasource_alias_id__isnull=True).values('datasource_alias_id', 'datasource_alias__name').distinct()
        }
        products = {
            row['project_product_id']: row['project_product__name']
            for row in queryset.exclude(project_product_id__isnull=True).values('project_product_id', 'project_product__name').distinct()
        }
        return ResponseData.success(RESPONSE_MSG_0001, {
            'datasource_type_options': [*({'key': key, 'title': title} for key, title in DataSourceTypeEnum.obj().items()),
                                        {'key': 'unrecorded', 'title': '历史未记录'}],
            'source_type_options': [{'key': value, 'title': DatasourceAuditSourceEnum.obj().get(value, value)} for value in source_types],
            'source_stage_options': [{'key': value, 'title': DatasourceAuditStageEnum.obj().get(value, value)} for value in source_stages],
            'status_options': [
                {'key': 'running', 'title': '执行中'},
                {'key': 'success', 'title': '成功'},
                {'key': 'fail', 'title': '失败'},
                {'key': 'timeout', 'title': '超时'},
                {'key': 'rolled_back', 'title': '已回滚'},
            ],
            'slow_options': [
                {'key': True, 'title': '慢执行'},
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
