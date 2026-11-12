# -*- coding: utf-8 -*-
# @ProjectProduct: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializers, ProjectProductSerializersC
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.test_center.services.project.project_product_cache import ProjectProductCacheService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses import (
    RESPONSE_MSG_0118,
    ResponseData,
)
from src.common.responses.model_crud import ModelCRUD


class ProjectProductCRUD(ModelCRUD):
    model = ProjectProduct
    queryset = ProjectProduct.objects.all()
    serializer_class = ProjectProductSerializersC
    serializer = ProjectProductSerializers
    page_permission_key = 'config.product'
    not_matching_str = ModelCRUD.not_matching_str + ['ui_client_type', 'api_client_type', 'owners']

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        """按当前用户的数据范围筛选项目产品"""
        return super().filter_queryset_by_data_scope(request, queryset).distinct()


class ProjectProductViews(ViewSet):
    model = ProjectProduct
    serializer_class = ProjectProductSerializers

    @staticmethod
    def filter_by_user_scope(request: Request, queryset):
        """按当前用户范围筛选项目产品"""
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def get_product_name(self, request: Request):
        """
        产品选项
        @param request:
        @return:
        """
        project_id = request.query_params.get('project_id')
        if project_id:
            queryset = self.model.objects.filter(project=project_id)
            allowed_ids = set(
                self.filter_by_user_scope(request, queryset).values_list('id', flat=True)
            )
            options = ProjectProductCacheService.get_options(int(project_id))
            data = [
                {'key': option['value'], 'title': option['label']}
                for option in options
                if option['value'] in allowed_ids
            ]
        else:
            queryset = self.model.objects.all()
            res = self.filter_by_user_scope(request, queryset).values_list('id', 'name')
            data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0118, data)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def product_all_module_name(self, request: Request):
        """
        产品和模块选项
        @param request:
        @return:
        """
        project_id = request.query_params.get('project_id')
        if project_id:
            queryset = self.model.objects.filter(project=project_id)
        else:
            queryset = self.model.objects.all()
        res = self.filter_by_user_scope(request, queryset).values_list('id', 'name')
        options = []
        for _id, name in res:
            product_module = ProductModule.objects.values_list('id', 'name').filter(project_product=_id)
            options.append({
                'value': _id,
                'label': name,
                'children': [{'value': __id, 'label': __name, } for __id, __name in product_module]
            })
        return ResponseData.success(RESPONSE_MSG_0118, options)
