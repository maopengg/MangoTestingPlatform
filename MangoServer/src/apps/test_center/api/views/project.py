# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from mangotools.enums import StatusEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_pytest.models import PytestProduct
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.apps.test_center.api.serializers.project import ProjectSerializers
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import TestObject, Project, ProjectProduct, ProductModule
from src.apps.test_center.services.project_product_cache import ProjectProductCacheService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses import (
    RESPONSE_MSG_0025,
    RESPONSE_MSG_0095,
    ResponseData,
)
from src.common.responses.model_crud import ModelCRUD


class ProjectCRUD(ModelCRUD):
    model = Project
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers
    serializer = ProjectSerializers
    page_permission_key = 'config.project'


class ProjectViews(ViewSet):
    model = Project
    serializer_class = ProjectSerializers

    @staticmethod
    def _allowed_product_queryset(request: Request):
        queryset = ProjectProduct.objects.all()
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()

    @classmethod
    def _allowed_project_queryset(cls, request: Request):
        product_queryset = cls._allowed_product_queryset(request)
        return Project.objects.filter(
            status=StatusEnum.SUCCESS.value,
            id__in=product_queryset.values_list('project_id', flat=True),
        )

    @classmethod
    def _product_config_project_queryset(cls, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None:
            return Project.objects.filter(status=StatusEnum.SUCCESS.value)
        permission_keys = PermissionMenuService.permission_keys_for_user(user)
        if (
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user) or
                'config.project:read' in permission_keys
        ):
            return Project.objects.filter(status=StatusEnum.SUCCESS.value)
        return cls._allowed_project_queryset(request)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def get_all_items(self, request: Request):
        """
        项目的ID和name，title选项专用
        @param request:
        @return:
        """
        items = self._allowed_project_queryset(request)
        data = [{'title': i.name, 'key': i.pk} for i in items]
        data.insert(0, {'title': '选择项目', 'key': None})
        return ResponseData.success(RESPONSE_MSG_0025, data)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def product_config_project_options(self, request: Request):
        """
        项目产品配置页新增/编辑产品时使用的项目选项。
        该场景需要允许选择还没有任何产品的启用项目，用于创建项目下的第一个产品。
        """
        items = self._product_config_project_queryset(request)
        data = [{'title': i.name, 'key': i.pk} for i in items]
        data.insert(0, {'title': '选择项目', 'key': None})
        return ResponseData.success(RESPONSE_MSG_0025, data)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def project_product_name(self, request: Request):
        """
        项目和产品的选项
        @param request:
        @return:
        """
        product_scope = self._allowed_product_queryset(request)
        book = self._allowed_project_queryset(request).values_list('id', 'name')
        options = []
        for _id, name in book:
            allowed_product_ids = set(
                product_scope.filter(project_id=_id).values_list('id', flat=True)
            )
            product_list = ProjectProductCacheService.get_options(_id)
            project = {
                'value': _id,
                'label': name,
                'children': []
            }
            for product_option in product_list:
                product_id = product_option['value']
                if product_id not in allowed_product_ids:
                    continue
                if request.query_params.get('client_type') == '1':
                    v = ProductModule.objects.values_list('id', 'name').filter(project_product=product_id)
                    project['children'].append({
                        'value': product_id,
                        'label': product_option['label'],
                        'children': [{'value': module_id, 'label': module_name} for module_id, module_name in v]})
                else:
                    project['children'].append(dict(product_option))
            options.append(project)
        return ResponseData.success(RESPONSE_MSG_0025, options)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def project_pytest_name(self, request: Request):
        """
        项目和产品的选项
        @param request:
        @return:
        """
        product_scope = self._allowed_product_queryset(request)
        book = self._allowed_project_queryset(request).values_list('id', 'name')
        active_pytest_project_ids = PytestProductSyncService.active_project_ids()
        options = []
        for _id, name in book:
            project = {
                'value': _id,
                'label': name,
                'children': []
            }
            product_list = product_scope.filter(project=_id)
            for i in product_list:
                pytest_product_list = PytestProduct.objects.values_list('id', 'name').filter(
                    project_product_id=i.id,
                    id__in=active_pytest_project_ids,
                )
                for product_id, product_name in pytest_product_list:
                    v = ProductModule.objects.values_list('id', 'name').filter(project_product=i.id)
                    project['children'].append({
                        'value': product_id,
                        'label': product_name,
                        'project_product_id': i.id,
                        'children': [{'value': module_id, 'label': module_name} for module_id, module_name in v]})
            options.append(project)
        return ResponseData.success(RESPONSE_MSG_0025, options)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def project_environment_name(self, request: Request):
        """
        项目测试环境选项
        @param request:
        @return:
        """
        product_scope = self._allowed_product_queryset(request)
        book = self._allowed_project_queryset(request).values_list('id', 'name')
        options = [{
            'value': -1,
            'label': '请选择测试环境',
            'children': []
        }]
        for _id, name in book:
            project_obj = {
                'value': _id,
                'label': name,
                'children': []
            }
            test_object_environment_list = []

            product_id_list = product_scope.values_list('id', flat=True).filter(project=_id)
            for product_id in product_id_list:
                test_object_list = TestObject.objects \
                    .filter(project_product=product_id)
                for test_object in test_object_list:
                    if test_object.environment not in test_object_environment_list:
                        test_object_environment_list.append(test_object.environment)
                        project_obj['children'].append({'value': test_object.id,
                                                        'label': EnvironmentEnum.get_value(test_object.environment),
                                                        })
            options.append(project_obj)
        return ResponseData.success(RESPONSE_MSG_0095, options)
