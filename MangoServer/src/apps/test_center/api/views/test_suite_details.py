# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import os

from django.db.models import Sum
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiCase, ApiCaseExecutionTrace
from src.apps.auto_api.services.execution_trace.builder import ApiCaseExecutionTraceBuilder
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.api.serializers.test_suite import TestSuiteSerializersC
from src.apps.test_center.api.serializers.test_suite_details import TestSuiteDetailsSerializers, \
    TestSuiteDetailsSerializersC
from src.apps.test_center.models import ExecutionResult, TestSuiteDetails, TestSuite
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.test_center.services.test_suite.api_report_export import ApiReportExportService
from src.apps.test_center.services.test_suite.detail_query import TestSuiteDetailQueryService
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.test_suite.failure_reason import TestSuiteFailureReasonService
from src.apps.test_center.services.test_suite.report_overview import TestSuiteReportOverviewService
from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService
from src.apps.test_center.services.test_suite.disposition import TestSuiteDispositionService
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.decorators.retry import db_connection_context
from src.common.responses import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0065,
    RESPONSE_MSG_0110,
    RESPONSE_MSG_0132,
    RESPONSE_MSG_0133,
    RESPONSE_MSG_0192,
    RESPONSE_MSG_0193,
    RESPONSE_MSG_0194,
    RESPONSE_MSG_0195,
    RESPONSE_MSG_0196,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0211,
    RESPONSE_MSG_0212,
    RESPONSE_MSG_0213,
    RESPONSE_MSG_0214,
    ResponseData,
)
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_msg import TEST_RESULT_FILTER_INVALID


class TestSuiteDetailsCRUD(ModelCRUD):
    http_method_names = ['get', 'head', 'options']
    model = TestSuiteDetails
    queryset = TestSuiteDetails.objects.all()
    serializer_class = TestSuiteDetailsSerializersC
    serializer = TestSuiteDetailsSerializers
    page_permission_key = 'report'

    @error_response('system')
    def get(self, request: Request):
        query_dict = {}
        for k, v in dict(request.query_params.lists()).items():
            if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
                query_dict[f'{k}__contains'] = v[0]
            else:
                query_dict[k] = v[0]
        del query_dict['pageSize']
        del query_dict['page']
        books = self.filter_queryset_by_data_scope(request, self.model.objects.filter(**query_dict)).order_by('-id')
        books = self.filter_queryset_by_data_scope(request, books)
        data_list, count = self.paging_list(
            request.query_params.get("pageSize"),
            request.query_params.get("page"),
            books,
            self.get_serializer_class()
        )
        count = books.aggregate(total=Sum('case_sum'))['total'] or count
        TestSuiteExecutionResultService.attach_summary(data_list)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            data_list,
            count
        )


class TestSuiteDetailsViews(ViewSet):
    model = TestSuiteDetails
    serializer_class = TestSuiteDetailsSerializers

    @staticmethod
    def _has_project_product_scope(request: Request, project_product_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @action(methods=['post'], detail=False)
    @error_response('system')
    def update_disposition(self, request: Request):
        detail_id = TestSuiteDispositionService.validate_id(request.data.get('id'))
        if not self._has_detail_scope(request, detail_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        values = {key: value for key, value in request.data.items() if key != 'id'}
        return ResponseData.success(RESPONSE_MSG_0001, TestSuiteDispositionService.update(detail_id, values))

    @classmethod
    def _has_suite_scope(cls, request: Request, test_suite_id) -> bool:
        project_product_id = TestSuite.objects.filter(id=test_suite_id).values_list('project_product_id',
                                                                                    flat=True).first()
        return cls._has_project_product_scope(request, project_product_id)

    @classmethod
    def _has_detail_scope(cls, request: Request, detail_id) -> bool:
        project_product_id = cls.model.objects.filter(id=detail_id).values_list('project_product_id', flat=True).first()
        return cls._has_project_product_scope(request, project_product_id)

    @classmethod
    def _has_api_case_scope(cls, request: Request, case_id) -> bool:
        project_product_id = ApiCase.objects.filter(id=case_id).values_list('project_product_id', flat=True).first()
        return cls._has_project_product_scope(request, project_product_id)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def execution_options(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, ApiConcurrencyService.capacity())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_retry(self, request: Request):
        if not self._has_suite_scope(request, request.query_params.get('test_suite_id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        requested_api_concurrency_limit = request.query_params.get('api_concurrency_limit')
        test_env, api_concurrency_limit = TestSuiteRetryService.retry_all(
            request.query_params.get('test_suite_id'),
            request.query_params.get('test_env'),
            requested_api_concurrency_limit,
            concurrency_override_provided=requested_api_concurrency_limit not in (None, ''),
        )
        return ResponseData.success(
            RESPONSE_MSG_0132,
            {
                'test_env': test_env,
                'api_concurrency_limit': api_concurrency_limit,
            },
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_retry(self, request: Request):
        if not self._has_detail_scope(request, request.query_params.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        TestSuiteRetryService.retry_detail(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0133)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def retry_failed(self, request: Request):
        suite_id = request.data.get('test_suite_id')
        if not self._has_suite_scope(request, suite_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        count = TestSuiteRetryService.retry_failed(suite_id)
        return ResponseData.success(RESPONSE_MSG_0132, {'retry_count': count})

    @action(methods=['get'], detail=False)
    @error_response('user')
    def test_suite_details_report(self, request):
        return ResponseData.success(
            RESPONSE_MSG_0110,
            TestSuiteReportOverviewService.overview(request),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_summary(self, request: Request):
        # 使用数据库连接上下文管理器确保连接被正确释放
        with db_connection_context():
            test_suite_id = request.query_params.get('test_suite_id')
            return ResponseData.success(RESPONSE_MSG_0065, TestSuiteSummaryService.summary_data(test_suite_id))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def execution_trace(self, request: Request):
        result_id = request.query_params.get('result_id')
        trace_id = request.query_params.get('trace_id')
        test_suite_detail_id = request.query_params.get('test_suite_detail_id')
        case_id = request.query_params.get('case_id')
        include_list = str(request.query_params.get('include_list', '')).lower() in ['1', 'true', 'yes']
        if not result_id and not trace_id and not test_suite_detail_id and not case_id:
            return ResponseData.fail(RESPONSE_MSG_0211)
        if result_id:
            if not str(result_id).isdigit():
                return ResponseData.fail(RESPONSE_MSG_0211)
            execution_result = ExecutionResult.objects.filter(id=result_id).only(
                'trace_id',
                'target_type',
                'target_id',
                'test_suite_detail_id',
            ).first()
            if not execution_result:
                return ResponseData.fail(RESPONSE_MSG_0211)
            trace_id = execution_result.trace_id
            test_suite_detail_id = None
            case_id = None
            if execution_result.test_suite_detail_id:
                if not self._has_detail_scope(request, execution_result.test_suite_detail_id):
                    return ResponseData.fail(RESPONSE_MSG_0210)
            elif execution_result.target_type == ExecutionResultService.TARGET_API_CASE:
                if not self._has_api_case_scope(request, execution_result.target_id):
                    return ResponseData.fail(RESPONSE_MSG_0210)
            else:
                return ResponseData.fail(RESPONSE_MSG_0210)
        detail_id = test_suite_detail_id
        if trace_id and not detail_id:
            detail_id = ApiCaseExecutionTrace.objects.filter(trace_id=trace_id).values_list(
                'test_suite_detail_id',
                flat=True,
            ).first()
        if detail_id and not self._has_detail_scope(request, detail_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if case_id and not self._has_api_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        data = ApiCaseExecutionTraceBuilder.get_trace_data(
            trace_id=trace_id,
            test_suite_detail_id=test_suite_detail_id,
            case_id=case_id,
            include_list=include_list,
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)


class TestSuiteDetailsShareViews(ViewSet):
    authentication_classes = []
    model = TestSuiteDetails
    serializer_class = TestSuiteDetailsSerializers

    @staticmethod
    def _summary_data(test_suite_id):
        return TestSuiteSummaryService.summary_data(test_suite_id)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_test_suite(self, request: Request):
        test_suite_id = request.query_params.get('id')
        model = TestSuite.objects.filter(id=test_suite_id).first()
        if not model:
            return ResponseData.fail(RESPONSE_MSG_0214)
        return ResponseData.success(RESPONSE_MSG_0001, TestSuiteSerializersC(instance=model).data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_details(self, request: Request):
        test_suite_id = request.query_params.get('test_suite_id')
        if not test_suite_id:
            return ResponseData.fail(RESPONSE_MSG_0212)
        if not str(test_suite_id).isdigit():
            return ResponseData.success(RESPONSE_MSG_0001, [], 0)
        query_dict = {'test_suite_id': test_suite_id}
        excluded = request.query_params.get('is_excluded')
        if excluded in ('true', 'false', '1', '0'):
            query_dict['is_excluded'] = excluded in ('true', '1')
        for key in ['status', 'type']:
            value = request.query_params.get(key)
            if value is not None and value != '':
                if not str(value).isdigit():
                    return ResponseData.success(RESPONSE_MSG_0001, [], 0)
                query_dict[key] = value
        books = self.model.objects.filter(**query_dict)
        books = TestSuiteDetailQueryService.filter_by_case_keyword(
            books,
            request.query_params.get('case_keyword'),
        ).order_by('-id')
        data_list, count = TestSuiteDetailsCRUD.paging_list(
            request.query_params.get("pageSize", 10000),
            request.query_params.get("page", 1),
            books,
            TestSuiteDetailsSerializersC
        )
        count = books.aggregate(total=Sum('case_sum'))['total'] or count
        TestSuiteExecutionResultService.attach_summary(data_list)
        return ResponseData.success(RESPONSE_MSG_0001, data_list, count)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_detail_result(self, request: Request):
        test_suite_detail_id = request.query_params.get('test_suite_detail_id')
        if not test_suite_detail_id:
            return ResponseData.fail(RESPONSE_MSG_0211)
        if not str(test_suite_detail_id).isdigit():
            return ResponseData.success(RESPONSE_MSG_0001, None)
        result_id = request.query_params.get('result_id')
        if result_id and not str(result_id).isdigit():
            return ResponseData.success(RESPONSE_MSG_0001, None)
        detail = self.model.objects.filter(id=test_suite_detail_id).select_related(
            'project_product',
            'test_suite',
        ).first()
        if not detail:
            return ResponseData.success(RESPONSE_MSG_0001, None)
        data = TestSuiteDetailsSerializersC(instance=detail).data
        if result_id:
            payload = TestSuiteExecutionResultService.get_payload_with_result_data(int(result_id))
            if not TestSuiteExecutionResultService.payload_matches_detail(detail, payload):
                return ResponseData.success(RESPONSE_MSG_0001, None)
            TestSuiteExecutionResultService.attach_children([data], payload_map={detail.id: payload})
        else:
            TestSuiteExecutionResultService.attach_children([data])
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_detail_result_options(self, request: Request):
        test_suite_detail_id = request.query_params.get('test_suite_detail_id')
        if not test_suite_detail_id:
            return ResponseData.fail(RESPONSE_MSG_0211)
        if not str(test_suite_detail_id).isdigit():
            return ResponseData.success(RESPONSE_MSG_0001, [])
        if not self.model.objects.filter(id=test_suite_detail_id).exists():
            return ResponseData.success(RESPONSE_MSG_0001, [])
        return ResponseData.success(
            RESPONSE_MSG_0001,
            TestSuiteExecutionResultService.get_payload_options(
                int(test_suite_detail_id),
                request.query_params.get('limit'),
            ),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def execution_trace(self, request: Request):
        trace_id = request.query_params.get('trace_id')
        test_suite_detail_id = request.query_params.get('test_suite_detail_id')
        case_id = request.query_params.get('case_id')
        include_list = str(request.query_params.get('include_list', '')).lower() in ['1', 'true', 'yes']
        if not trace_id and not test_suite_detail_id and not case_id:
            return ResponseData.fail(RESPONSE_MSG_0211)
        data = ApiCaseExecutionTraceBuilder.get_trace_data(
            trace_id=trace_id,
            test_suite_detail_id=test_suite_detail_id,
            case_id=case_id,
            include_list=include_list,
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_summary(self, request: Request):
        test_suite_id = request.query_params.get('test_suite_id')
        if not test_suite_id:
            return ResponseData.fail(RESPONSE_MSG_0212)
        if not str(test_suite_id).isdigit():
            return ResponseData.fail(RESPONSE_MSG_0213)
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return ResponseData.fail(RESPONSE_MSG_0214)
        return ResponseData.success(RESPONSE_MSG_0065, self._summary_data(test_suite_id))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_failure_reasons(self, request: Request):
        test_suite_id = request.query_params.get('test_suite_id')
        if not test_suite_id:
            return ResponseData.fail(RESPONSE_MSG_0212)
        if not str(test_suite_id).isdigit():
            return ResponseData.fail(RESPONSE_MSG_0213)
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return ResponseData.fail(RESPONSE_MSG_0214)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            TestSuiteFailureReasonService.top_failure_reasons(int(test_suite_id)),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def post_api_export(self, request: Request):
        test_suite_id = request.data.get('test_suite_id')
        status = request.data.get('status')
        if not test_suite_id or not str(test_suite_id).isdigit():
            return ResponseData.fail(RESPONSE_MSG_0212)
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return ResponseData.fail(RESPONSE_MSG_0214)
        status_value = None
        if status not in [None, '', 'all']:
            if not str(status).isdigit():
                return ResponseData.fail(TEST_RESULT_FILTER_INVALID)
            status_value = int(status)
        task = ApiReportExportService.start(int(test_suite_id), status_value)
        return ResponseData.success(RESPONSE_MSG_0192, task)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_api_export_status(self, request: Request):
        task_id = request.query_params.get('task_id')
        task = ApiReportExportService.get(task_id)
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0194)
        return ResponseData.success(RESPONSE_MSG_0193, task)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def download_api_export(self, request: Request):
        task_id = request.query_params.get('task_id')
        task = ApiReportExportService.get(task_id)
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0194)
        if task.get('status') != 'success':
            return ResponseData.fail(RESPONSE_MSG_0195)
        file_path = task.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return ResponseData.fail(RESPONSE_MSG_0196)
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=task.get('file_name') or os.path.basename(file_path),
        )
