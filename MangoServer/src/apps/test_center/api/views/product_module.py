# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-10-12 18:14
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.test_center.api.serializers.product_module import ProductModulePathSerializer, \
    ProductModuleSerializersC
from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers
from src.apps.test_center.models import ProductModule
from src.apps.test_center.services.product_module_cache import ProductModuleCacheService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0031,
    RESPONSE_MSG_0210,
)


class ProductModuleCRUD(ModelCRUD):
    model = ProductModule
    queryset = ProductModule.objects.all()
    serializer_class = ProductModuleSerializersC
    page_permission_key = 'config.product'
    # post专用序列化器
    serializer = ProductModuleSerializers


class ProductModuleViews(ViewSet):
    model = ProductModule
    serializer_class = ProductModuleSerializers
    action_permission_map = {
        'create_path': 'config.product:create',
    }

    @staticmethod
    def _filter_by_user_scope(request: Request, queryset):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def get_module_name(self, request: Request):
        """
        模块的ID和name
        @param request:
        @return:
        """
        project_product_id = request.query_params.get('project_product_id')
        if project_product_id:
            if not ProductModuleCRUD().has_data_scope_permission(
                    request,
                    {'project_product': project_product_id},
            ):
                return ResponseData.success(RESPONSE_MSG_0031, [])
            data = ProductModuleCacheService.get_names(
                int(project_product_id),
                lambda: self._module_name_data(project_product_id),
            )
        else:
            queryset = self._filter_by_user_scope(
                request,
                self.model.objects.select_related('parent', 'parent__parent'),
            )
            data = self._serialize_module_names(queryset)
        return ResponseData.success(RESPONSE_MSG_0031, data)

    @classmethod
    def _module_name_data(cls, project_product_id):
        queryset = cls.model.objects.select_related('parent', 'parent__parent').filter(
            project_product_id=project_product_id
        )
        return cls._serialize_module_names(queryset)

    @classmethod
    def _serialize_module_names(cls, queryset):
        return [
            {
                'key': item.id,
                'title': item.name,
                'level': item.level,
                'parent_id': item.parent_id,
                'path': cls._module_path(item),
            }
            for item in queryset
        ]

    @staticmethod
    def _module_path(module):
        names = []
        current = module
        while current:
            names.append(current.name)
            current = current.parent
        return ' / '.join(reversed(names))

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def tree(self, request: Request):
        project_product_id = request.query_params.get('project_product_id')
        if project_product_id:
            if not ProductModuleCRUD().has_data_scope_permission(
                    request,
                    {'project_product': project_product_id},
            ):
                return ResponseData.success(RESPONSE_MSG_0031, [])
            roots = ProductModuleCacheService.get_tree(
                int(project_product_id),
                lambda: self._module_tree_data(project_product_id),
            )
        else:
            queryset = self._filter_by_user_scope(
                request,
                self.model.objects.select_related('parent').order_by('sort', 'id'),
            )
            roots = self._build_module_tree(list(queryset))
        return ResponseData.success(RESPONSE_MSG_0031, roots)

    @classmethod
    def _module_tree_data(cls, project_product_id):
        modules = list(
            cls.model.objects.select_related('parent')
            .filter(project_product_id=project_product_id)
            .order_by('sort', 'id')
        )
        return cls._build_module_tree(modules)

    @staticmethod
    def _build_module_tree(modules):
        node_map = {
            item.id: {
                'id': item.id,
                'key': item.id,
                'name': item.name,
                'title': item.name,
                'level': item.level or 1,
                'sort': item.sort,
                'parent_id': item.parent_id,
                'project_product_id': item.project_product_id,
                'children': [],
            }
            for item in modules
        }
        roots = []
        for item in modules:
            node = node_map[item.id]
            parent = node_map.get(item.parent_id)
            if parent:
                parent['children'].append(node)
            else:
                roots.append(node)
        return roots

    @action(methods=['POST'], detail=False)
    @error_response('user')
    def create_path(self, request: Request):
        serializer = ProductModulePathSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project_product = serializer.validated_data['project_product']
        if not ProductModuleCRUD().has_data_scope_permission(
                request,
                {'project_product': project_product.id},
        ):
            return ResponseData.fail(RESPONSE_MSG_0210)
        module = serializer.save(update_user_id=ProductModuleCRUD.get_request_user_id(request))
        return ResponseData.success(
            RESPONSE_MSG_0002,
            ProductModuleSerializers(instance=module).data,
        )
