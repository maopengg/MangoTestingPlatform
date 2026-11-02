# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_pytest.api.serializers.pytest_product import PytestProductSerializers, PytestProductSerializersC
from src.apps.auto_pytest.api.views.pytest_repository import _can_browse_all_repositories, _repository
from src.apps.auto_pytest.models import PytestProduct
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.apps.test_center.models import ProductModule
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0154,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0306,
    RESPONSE_MSG_0313,
    RESPONSE_MSG_0314,
)


class PytestProductCRUD(ModelCRUD):
    model = PytestProduct
    queryset = PytestProduct.objects.annotate(case_count=Count('pytestcase', distinct=True))
    serializer_class = PytestProductSerializersC
    serializer = PytestProductSerializers
    page_permission_key = 'pytest.product'

    @error_response('pytest')
    def post(self, request: Request):
        return ResponseData.fail(RESPONSE_MSG_0314)

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset)
        return queryset.filter(id__in=PytestProductSyncService.active_project_ids())


class PytestProductViews(ViewSet):
    model = PytestProduct
    serializer_class = PytestProductSerializers

    @staticmethod
    def _has_product_scope(request: Request, product_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        project_product_id = PytestProduct.objects.filter(id=product_id).values_list(
            'project_product_id',
            flat=True,
        ).first()
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @action(methods=['post'], detail=False)
    @error_response('pytest')
    def pytest_import(self, request: Request):
        repository = _repository(
            request.data.get('repository_id') or request.data.get('repository'),
            request,
        )
        project_product_id = PytestProductCRUD._relation_id(request.data.get('project_product'))
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None:
            try:
                has_scope = ProjectProductScopeService.has_project_product(user, int(project_product_id))
            except (TypeError, ValueError):
                has_scope = False
            if not has_scope:
                return ResponseData.fail(RESPONSE_MSG_0210)
        product = PytestProductSyncService.import_project(
            project_path=request.data.get('file_name'),
            test_dirs=request.data.get('test_dir'),
            name=request.data.get('name'),
            auto_type=request.data.get('auto_type'),
            project_product_id=project_product_id,
            repository_id=repository.id,
            working_directory=request.data.get('working_directory'),
            pytest_config_path=request.data.get('pytest_config_path'),
            operator_id=PytestProductCRUD.get_request_user_id(request),
        )
        data = PytestProductSerializers(instance=product).data
        return ResponseData.success(RESPONSE_MSG_0313, data=data)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_test_directories(self, request: Request):
        product_id = request.query_params.get('id')
        project_path = request.query_params.get('project_path')
        if product_id:
            if not self._has_product_scope(request, product_id):
                return ResponseData.fail(RESPONSE_MSG_0210)
            product = PytestProduct.objects.get(id=product_id)
            project_path = product.file_name
            repository_id = product.repository_id
        else:
            repository_id = request.query_params.get('repository_id')
            if repository_id:
                if not _can_browse_all_repositories(request):
                    return ResponseData.fail(RESPONSE_MSG_0210)
                _repository(repository_id, request)
        data = PytestProductSyncService.test_directory_options_for_path(project_path, repository_id)
        return ResponseData.success(RESPONSE_MSG_0306, data=data)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_project_name(self, request: Request):
        """
        获取pytest的项目名称
        @param request:
        @return:
        """
        project_product_id = request.query_params.get('project_product_id')
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None:
            try:
                has_scope = ProjectProductScopeService.has_project_product(user, int(project_product_id))
            except (TypeError, ValueError):
                has_scope = False
            if not has_scope:
                return ResponseData.fail(RESPONSE_MSG_0210)
        res = self.model.objects \
            .filter(
            project_product_id=project_product_id,
            id__in=PytestProductSyncService.active_project_ids(),
        ) \
            .values_list('id', 'name')
        data_list = []
        for _id, name in res:
            v = ProductModule.objects.values_list('id', 'name').filter(
                project_product=project_product_id)
            data_list.append({
                'value': _id,
                'label': name,
                'children': [{'value': module_id, 'label': module_name} for module_id, module_name in v]
            })
        return ResponseData.success(RESPONSE_MSG_0154, data_list)
