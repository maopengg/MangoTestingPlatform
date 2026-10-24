from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_pytest.api.serializers.pytest_case import PytestCaseSerializersC
from src.apps.auto_pytest.api.serializers.pytest_case_mutation import PytestCaseSerializers
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector
from src.apps.auto_pytest.services.case_publication import PytestCasePublicationService
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
)
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_pytest.services.base.method_nodes import PytestMethodNodeService
from src.apps.auto_pytest.services.batch_execution import PytestCaseBatchExecutionService
from src.apps.auto_pytest.services.file_management import PytestFileManagementService
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.apps.auto_pytest.services.test_case.ai_inference import PytestCaseAiInferenceService
from src.apps.auto_pytest.services.test_case.batch_update import PytestCaseBatchUpdateService
from src.apps.auto_pytest.services.test_case.directory_tree import PytestCaseDirectoryTreeService
from src.apps.auto_pytest.services.test_case.module_binding import PytestCaseModuleBindingService
from src.apps.auto_pytest.services.test_case.sync import PytestCaseSyncService
from src.apps.auto_pytest.services.test_case.test_case import TestCase
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0078,
    RESPONSE_MSG_0084,
    RESPONSE_MSG_0085,
    RESPONSE_MSG_0086,
    RESPONSE_MSG_0166,
    RESPONSE_MSG_0167,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0272,
    RESPONSE_MSG_0278,
    RESPONSE_MSG_0280,
    RESPONSE_MSG_0315,
    RESPONSE_MSG_0317,
    RESPONSE_MSG_0319,
)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏


class PytestCaseCRUD(ModelCRUD):
    model = PytestCase
    queryset = PytestCase.objects.all()
    serializer_class = PytestCaseSerializersC
    serializer = PytestCaseSerializers
    page_permission_key = 'pytest.case'

    @error_response('pytest')
    def get(self, request: Request):
        queryset = self.filter_queryset_by_data_scope(request, self.queryset.all())
        queryset = PytestCasePublicationSelector.filter_search(queryset, request.query_params)
        queryset = PytestCasePublicationSelector.with_owner(queryset, request.user['id'])
        if request.query_params.get('page') and request.query_params.get('pageSize'):
            items, count = self.paging_list(request.query_params['pageSize'], request.query_params['page'],
                                           queryset, self.serializer_class)
            return ResponseData.success(RESPONSE_MSG_0084, items, count)
        queryset = self.serializer_class.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0084, self.serializer_class(queryset, many=True).data, queryset.count())

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset)
        return queryset.filter(
            project_product_id__in=PytestProductSyncService.active_project_ids(),
        )


class PytestCaseViews(ViewSet):
    model = PytestCase
    serializer_class = PytestCaseSerializers
    action_permission_map = {
        'pytest_update': 'pytest.case:edit',
        'pytest_read': 'pytest.case:detail',
        'pytest_write': 'pytest.case:edit',
        'pytest_test_case': 'pytest.case:execute',
        'pytest_test_case_batch': 'pytest.case:execute',
        'pytest_method_nodes': 'pytest.case:detail',
        'pytest_directory_tree': 'pytest.case:detail',
        'set_module': 'pytest.case:edit',
        'batch_update': 'pytest.case:edit',
        'ai_infer': 'pytest.case:edit',
        'set_publication': 'pytest.case:publish',
        'publication_review': 'pytest.case:publish',
    }

    @staticmethod
    def _has_case_scope(request: Request, case_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        project_product_id = PytestCase.objects.filter(id=case_id).values_list(
            'project_product__project_product_id',
            flat=True,
        ).first()
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _has_product_scope(request: Request, product: PytestProduct) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        try:
            return ProjectProductScopeService.has_project_product(
                user,
                int(product.project_product_id),
            )
        except (TypeError, ValueError):
            return False

    @classmethod
    def _has_cases_scope(cls, request: Request, case_ids) -> bool:
        return all(cls._has_case_scope(request, case_id) for case_id in case_ids or [])

    @action(methods=['post'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        project_id = request.data.get('project_id')
        if not project_id:
            return ResponseData.fail(RESPONSE_MSG_0166)

        product = PytestProduct.objects.filter(id=project_id).first()
        if not product:
            return ResponseData.fail(RESPONSE_MSG_0167)
        if not self._has_product_scope(request, product):
            return ResponseData.fail(RESPONSE_MSG_0210)

        result = PytestCaseSyncService.sync(
            project_id,
            PytestCaseCRUD.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0078, result, value=(result["created_count"],))

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        if not self._has_case_scope(request, request.query_params.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = PytestFileManagementService.read_case_file(
            request.query_params.get('id'),
            request.query_params.get('file_type', 'py'),
        )
        return ResponseData.success(RESPONSE_MSG_0084, data=result)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        if not self._has_case_scope(request, request.data.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = PytestFileManagementService.write_case_file(
            request.data.get('id'),
            request.data.get('file_type', 'py'),
            request.data.get('file_content'),
            PytestCaseCRUD.get_request_user_id(request),
            expected_commit=request.data.get('expected_commit'),
            expected_content_hash=request.data.get('expected_content_hash'),
        )
        return ResponseData.success(RESPONSE_MSG_0085, data=result)

    @action(methods=['GET'], detail=False)
    @error_response('pytest')
    def pytest_test_case(self, request: Request):
        if not self._has_case_scope(request, request.query_params.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        report_data = TestCase(request.user.get('username')) \
            .test_case(
            request.query_params.get('id'),
            int(request.query_params.get("test_env")),
            nodeid=request.query_params.get("nodeid"),
            node_type=request.query_params.get("node_type"),
            class_name=request.query_params.get("class_name"),
            method_name=request.query_params.get("method_name"),
            parameter_id=request.query_params.get("parameter_id"),
        )
        return ResponseData.success(
            RESPONSE_MSG_0086,
            data=TestCase.public_dispatch_data(report_data),
        )

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_test_case_batch(self, request: Request):
        case_ids = PytestCaseBatchExecutionService.normalize_case_ids(
            request.data.get('case_id_list')
        )
        if not self._has_cases_scope(request, case_ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = PytestCaseBatchExecutionService.execute(
            case_ids=case_ids,
            test_env=request.data.get('test_env'),
            user_id=request.user['id'],
        )
        return ResponseData.success(RESPONSE_MSG_0272, data=result)

    @action(methods=['put'], detail=False)
    @error_response('pytest')
    def set_publication(self, request: Request):
        try:
            case_id = int(request.data.get('case_id'))
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0280)
        target_status = request.data.get('target_status')
        if case_id <= 0:
            return ResponseData.fail(RESPONSE_MSG_0280)
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        case = PytestCasePublicationService.transition(case_id, target_status, operator_id=request.user['id'])
        return ResponseData.success(
            RESPONSE_MSG_0278,
            {
                'id': case_id,
                'publication_status': case.publication_status,
                'asset_status': case.asset_status,
            },
        )

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def publication_review(self, request: Request):
        case_id = request.query_params.get('case_id')
        if not str(case_id or '').isdigit():
            return ResponseData.fail(RESPONSE_MSG_0280)
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        from src.apps.auto_pytest.selectors.publication_review import PytestPublicationReviewSelector
        result = PytestPublicationReviewSelector.review(int(case_id), request.user['id'])
        user = getattr(request.user, 'user_obj', None)
        if user is None or 'pytest.case:detail' not in PermissionMenuService.permission_keys_for_user(user):
            result.pop('configuration_details', None)
        return ResponseData.success(RESPONSE_MSG_0084, result)

    @action(methods=['GET'], detail=False)
    @error_response('pytest')
    def pytest_method_nodes(self, request: Request):
        if not self._has_case_scope(request, request.query_params.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        file_data = PytestFileManagementService.read_case_file(
            request.query_params.get('id'),
            'py',
        )
        return ResponseData.success(
            RESPONSE_MSG_0084,
            data=PytestMethodNodeService.list_nodes(
                file_data['path'],
                file_data['content'],
            ),
        )

    @action(methods=['GET'], detail=False)
    @error_response('pytest')
    def pytest_directory_tree(self, request: Request):
        queryset = PytestCaseCRUD().filter_queryset_by_data_scope(
            request,
            PytestCase.objects.filter(
                project_product_id__in=PytestProductSyncService.active_project_ids(),
            ),
        )
        queryset = PytestCasePublicationSelector.filter_search(queryset, request.query_params)
        project_product_id = request.query_params.get('project_product_id')
        if project_product_id:
            try:
                project_product_id = int(project_product_id)
            except (TypeError, ValueError):
                queryset = queryset.none()
            else:
                queryset = queryset.filter(
                    project_product__project_product_id=project_product_id,
                )
        repository_id = request.query_params.get('repository_id')
        if repository_id:
            try:
                repository_id = int(repository_id)
            except (TypeError, ValueError):
                queryset = queryset.none()
            else:
                queryset = queryset.filter(project_product__repository_id=repository_id)
        pytest_project_id = request.query_params.get('pytest_project_id')
        if pytest_project_id:
            try:
                pytest_project_id = int(pytest_project_id)
            except (TypeError, ValueError):
                queryset = queryset.none()
            else:
                queryset = queryset.filter(project_product_id=pytest_project_id)
        keyword = str(request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(file_path__icontains=keyword)
                | Q(name__icontains=keyword)
                | Q(project_product__name__icontains=keyword)
                | Q(project_product__repository__name__icontains=keyword)
            )
        raw_module_ids = [
            item.strip() for item in request.query_params.get('module_ids', '').split(',')
            if item.strip()
        ]
        try:
            module_ids = [int(item) for item in raw_module_ids]
        except ValueError:
            module_ids = []
            queryset = queryset.none()
        if module_ids:
            queryset = queryset.filter(module_id__in=module_ids)
        return ResponseData.success(
            RESPONSE_MSG_0084,
            data=PytestCaseDirectoryTreeService.build(queryset),
        )

    @action(methods=['PUT'], detail=False)
    @error_response('pytest')
    def set_module(self, request: Request):
        queryset = PytestCaseCRUD().filter_queryset_by_data_scope(
            request,
            PytestCase.objects.all(),
        )
        result = PytestCaseModuleBindingService.bind(
            queryset,
            request.data.get('case_ids'),
            request.data.get('module_id'),
            PytestCaseCRUD.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0315, data=result)

    @action(methods=['PUT'], detail=False)
    @error_response('pytest')
    def batch_update(self, request: Request):
        updates = PytestCaseBatchUpdateService.normalize_updates(
            request.data.get('updates'),
        )
        case_ids = [item['id'] for item in updates]
        queryset = PytestCaseCRUD().filter_queryset_by_data_scope(
            request,
            PytestCase.objects.all(),
        )
        if queryset.filter(id__in=case_ids).count() != len(case_ids):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = PytestCaseBatchUpdateService.update(
            queryset,
            updates,
            PytestCaseCRUD.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0317, data=result)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def ai_infer(self, request: Request):
        case_ids = PytestCaseAiInferenceService.normalize_case_ids(
            request.data.get('case_ids'),
        )
        queryset = PytestCaseCRUD().filter_queryset_by_data_scope(
            request,
            PytestCase.objects.all(),
        )
        result = PytestCaseAiInferenceService.infer(queryset, case_ids)
        return ResponseData.success(RESPONSE_MSG_0319, data=result)
