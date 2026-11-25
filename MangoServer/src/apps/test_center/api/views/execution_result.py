from datetime import datetime, time

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.cache import patch_vary_headers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiCase
from src.apps.test_center.models import ExecutionResult
from src.apps.test_center.enums.content_search import ContentSearchKindEnum
from src.apps.test_center.services.diagnostics.api_case_diagnosis import ApiCaseDiagnosisService
from src.apps.test_center.services.diagnostics.assertion_diagnosis import AssertionDiagnosisService
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.test_center.services.results.result_file import ExecutionResultFileService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses import (
    ResponseData,
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0246,
)


class ExecutionResultViews(ViewSet):

    @action(methods=['post'], detail=False)
    @error_response('test_center')
    def search_start(self, request):
        """按项目产品、被测环境和单日检索自动化执行内容"""
        from src.apps.test_center.services.results.content_search import ExecutionContentSearchService
        return ResponseData.success(RESPONSE_MSG_0001, ExecutionContentSearchService.start(
            request.user.user_obj, ContentSearchKindEnum.AUTOMATION.value, request.data))

    @action(methods=['get'], detail=False)
    @error_response('test_center')
    def search_status(self, request):
        """查看自动化执行内容检索进度及分页命中记录"""
        from src.apps.test_center.services.results.content_search import ExecutionContentSearchService
        return ResponseData.success(RESPONSE_MSG_0001, ExecutionContentSearchService.get(
            request.user.user_obj, ContentSearchKindEnum.AUTOMATION.value, request.query_params.get('task_id'), request.query_params.get('page', 1)))

    @action(methods=['post'], detail=False)
    @error_response('test_center')
    def search_cancel(self, request):
        """取消本人发起的自动化执行内容检索"""
        from src.apps.test_center.services.results.content_search import ExecutionContentSearchService
        return ResponseData.success(RESPONSE_MSG_0001, ExecutionContentSearchService.cancel(
            request.user.user_obj, ContentSearchKindEnum.AUTOMATION.value, request.data.get('task_id')))

    @staticmethod
    def _visible_results(request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        return ExecutionResultService.visible_results(user)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def analyze_assertions(self, request: Request):
        """分析自动化执行结果中的失败断言"""
        return ResponseData.success(
            RESPONSE_MSG_0001,
            AssertionDiagnosisService.analyze(request.data.get('assertions')),
        )

    @staticmethod
    def _case_analysis_result(request: Request, raw_id):
        if not str(raw_id or '').isdigit():
            return None
        result = ExecutionResult.objects.filter(id=int(raw_id),
                                                target_type=ExecutionResultService.TARGET_API_CASE).first()
        if result is None:
            return None
        product_id = ApiCase.objects.filter(id=result.target_id).values_list('project_product_id', flat=True).first()
        if product_id is None:
            return None
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None:
            return None
        if not PermissionMenuService.is_effective_super_admin(user):
            if not ProjectProductScopeService.has_project_product(user, product_id):
                return None
        return result

    @action(methods=['get'], detail=False)
    @error_response('system')
    def preview_case_analysis(self, request: Request):
        """预览 API 用例失败分析范围"""
        result = self._case_analysis_result(request, request.query_params.get('result_id'))
        if result is None:
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(RESPONSE_MSG_0001, ApiCaseDiagnosisService.preview(result))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def analyze_case(self, request: Request):
        """分析 API 用例执行失败原因"""
        result = self._case_analysis_result(request, request.data.get('result_id'))
        if result is None:
            return ResponseData.fail(RESPONSE_MSG_0210)
        focus_index = request.data.get('focus_index')
        if focus_index is not None and (type(focus_index) is not int):
            return ResponseData.fail(RESPONSE_MSG_0003)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseDiagnosisService.analyze(result, request.data.get('scope') or 'auto', focus_index),
        )

    @staticmethod
    def build_filters(request: Request) -> dict | None:
        """解析执行结果查询条件"""
        filters = {}
        for key in ['source_type', 'target_type']:
            value = request.query_params.get(key)
            if value:
                filters[key] = value
        for key in ['target_id', 'revision_id', 'release_id', 'test_env', 'test_suite_id', 'test_suite_detail_id']:
            value = request.query_params.get(key)
            if value not in [None, '']:
                if not str(value).isdigit():
                    return None
                filters[key] = int(value)
        if request.query_params.get('revision_id_isnull') in ['1', 'true', 'True']:
            filters['revision_id__isnull'] = True
        if not filters.get('test_suite_detail_id') and (not filters.get('target_type') or not filters.get('target_id')):
            return None
        return filters

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_list(self, request: Request):
        """获取自动化执行结果列表"""
        filters = self.build_filters(request)
        if filters is None:
            return ResponseData.fail(RESPONSE_MSG_0003)
        page = int(request.query_params.get('page') or 1)
        page_size = int(request.query_params.get('pageSize') or 20)
        data, total = ExecutionResultService.result_options(filters, page, page_size,
                                                            queryset=self._visible_results(request))
        return ResponseData.success(RESPONSE_MSG_0001, data, total)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_detail(self, request: Request):
        """获取自动化执行结果详情"""
        result_id = request.query_params.get('id')
        if not result_id or not str(result_id).isdigit():
            return ResponseData.fail(RESPONSE_MSG_0003)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ExecutionResultService.result_detail(int(result_id), queryset=self._visible_results(request), prefer_file=True),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_content(self, request: Request):
        """读取并流式返回完整执行结果文件"""
        result_id = request.query_params.get('id')
        if not result_id or not str(result_id).isdigit():
            return ResponseData.fail(RESPONSE_MSG_0003)
        result_file, file_name = ExecutionResultService.open_result_file(int(result_id),
                                                                         queryset=self._visible_results(request))
        if result_file is None:
            return ResponseData.fail(RESPONSE_MSG_0003)
        result_file, encoding = ExecutionResultFileService.transport(result_file, request.headers.get('Accept-Encoding'))
        response = FileResponse(result_file, content_type='application/json')
        if encoding:
            response['Content-Encoding'] = encoding
        if file_name.endswith('.gz'):
            file_name = file_name[:-3]
        response['Content-Disposition'] = f'inline; filename="{file_name}"'
        response['Cache-Control'] = 'private, no-store'
        patch_vary_headers(response, ['Accept-Encoding'])
        return response

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_latest(self, request: Request):
        """获取最新完整执行结果"""
        filters = self.build_filters(request)
        if filters is None:
            return ResponseData.fail(RESPONSE_MSG_0003)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ExecutionResultService.latest_result_detail(filters, queryset=self._visible_results(request), prefer_file=True),
        )

    @staticmethod
    def _parse_datetime(value: str, end_of_day: bool = False):
        parsed = parse_datetime(value)
        if parsed is None:
            parsed_date = parse_date(value)
            if parsed_date is None:
                return None
            parsed = datetime.combine(
                parsed_date,
                time.max if end_of_day else time.min,
            )
        if settings.USE_TZ and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    @classmethod
    def build_admin_filters(cls, request: Request) -> dict | None:
        """解析执行结果管理页查询条件"""
        filters = {}
        integer_filters = {
            'id': 'id',
            'target_id': 'target_id',
            'status': 'status',
            'test_env': 'test_env',
            'trigger_user_id': 'trigger_user_id',
            'test_suite_id': 'test_suite_id',
            'test_suite_detail_id': 'test_suite_detail_id',
            'revision_id': 'revision_id',
            'release_id': 'release_id',
        }
        for query_key, filter_key in integer_filters.items():
            value = request.query_params.get(query_key)
            if value in [None, '']:
                continue
            if not str(value).isdigit():
                return None
            filters[filter_key] = int(value)

        for query_key, filter_key in {
            'id__in': 'id__in',
            'status__in': 'status__in',
            'test_env__in': 'test_env__in',
            'trigger_user_id__in': 'trigger_user_id__in',
        }.items():
            raw_values = request.query_params.getlist(query_key)
            values = [
                item.strip()
                for raw_value in raw_values
                for item in str(raw_value).split(',')
                if item.strip()
            ]
            if not values:
                if query_key == 'id__in' and query_key in request.query_params:
                    return None
                continue
            if any(not value.isdigit() for value in values):
                return None
            filters[filter_key] = [int(value) for value in values]

        for key in ['source_type', 'target_type']:
            value = request.query_params.get(key)
            if value:
                filters[key] = value
        for key in ['source_type', 'target_type']:
            query_key = f'{key}__in'
            values = [
                item.strip()
                for raw_value in request.query_params.getlist(query_key)
                for item in str(raw_value).split(',')
                if item.strip()
            ]
            if values:
                filters[query_key] = values
        for key in ['trace_id', 'task_id', 'error_message']:
            value = request.query_params.get(key)
            if value:
                filters[f'{key}__icontains'] = value

        is_latest = request.query_params.get('is_latest')
        if is_latest not in [None, '']:
            if str(is_latest).lower() not in ['true', 'false']:
                return None
            filters['is_latest'] = str(is_latest).lower() == 'true'

        result_state = request.query_params.get('result_state')
        if result_state:
            if result_state not in ['available', 'cleaned', 'empty']:
                return None
            filters['result_state'] = result_state
        result_states = [
            item.strip()
            for raw_value in request.query_params.getlist('result_state__in')
            for item in str(raw_value).split(',')
            if item.strip()
        ]
        if result_states:
            if any(value not in ['available', 'cleaned', 'empty'] for value in result_states):
                return None
            filters['result_state__in'] = result_states

        create_time_start = request.query_params.get('create_time_start')
        create_time_end = request.query_params.get('create_time_end')
        if create_time_start:
            start = cls._parse_datetime(create_time_start)
            if start is None:
                return None
            filters['create_time__gte'] = start
        if create_time_end:
            end = cls._parse_datetime(create_time_end, end_of_day=True)
            if end is None:
                return None
            filters['create_time__lte'] = end
        if (
                filters.get('create_time__gte')
                and filters.get('create_time__lte')
                and filters['create_time__gte'] > filters['create_time__lte']
        ):
            return None
        return filters

    @action(methods=['get'], detail=False)
    @error_response('system')
    def admin_list(self, request: Request):
        """获取执行结果管理列表"""
        filters = self.build_admin_filters(request)
        if filters is None:
            return ResponseData.fail(RESPONSE_MSG_0003)
        try:
            page = max(int(request.query_params.get('page') or 1), 1)
            page_size = min(max(int(request.query_params.get('pageSize') or 20), 1), 200)
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0003)
        data, total = ExecutionResultService.admin_result_options(
            filters,
            page,
            page_size,
        )
        return ResponseData.success(RESPONSE_MSG_0001, data, total)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def admin_config(self, request: Request):
        """获取完整执行结果保留策略与清理统计"""
        from src.apps.task_center.services.scheduling.system_job import SystemJobService

        data = ExecutionResultService.admin_config()
        cleanup_job = SystemJobService.get_job('clean_execution_result_data')
        data.update({
            'cleanup_job_name': cleanup_job.name if cleanup_job else None,
            'cleanup_description': cleanup_job.description if cleanup_job else None,
            'cleanup_cron': cleanup_job.cron if cleanup_job else None,
            'next_cleanup_at': (
                SystemJobService.next_fire_at(cleanup_job.cron)
                if cleanup_job
                else None
            ),
        })
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def admin_cleanup(self, request: Request):
        """清理过期完整执行结果并保留执行记录"""
        retention_days = ExecutionResultService.retention_days()
        result = ExecutionResultService.cleanup_expired(
            retention_days,
        )
        return ResponseData.success(
            RESPONSE_MSG_0246,
            result,
        )
