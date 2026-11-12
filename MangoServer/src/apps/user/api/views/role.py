# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 角色表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.user.api.serializers.user import RoleSerializers
from src.apps.user.services.authorization.permission import GUEST_ROLE_NAME, PermissionMenuService
from src.apps.user.services.authorization.role_authorization import RoleAuthorizationService
from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService
from src.apps.user.services.authorization.endpoint_catalog import grouped_endpoint_catalog, fixed_endpoint_tree
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0032, RESPONSE_MSG_0205, RESPONSE_MSG_0206, RESPONSE_MSG_0215
from ...models import Role


class RoleCRUD(ModelCRUD):
    model = Role
    queryset = Role.objects.defer('authorization')
    serializer_class = RoleSerializers
    serializer = RoleSerializers

    @staticmethod
    def is_guest_role_id(role_id):
        """判断指定角色是否为游客角色"""
        return Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists()

    @error_response('user')
    def put(self, request: Request):
        """修改角色"""
        if self.is_guest_role_id(request.data.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0215)
        return super().put(request)

    @error_response('user')
    def delete(self, request: Request):
        """删除角色"""
        role_id = request.query_params.get('id')
        role_ids = request.query_params.getlist('id[]')
        if self.is_guest_role_id(role_id) or Role.objects.filter(
                id__in=role_ids,
                name=GUEST_ROLE_NAME
        ).exists():
            return ResponseData.fail(RESPONSE_MSG_0215)
        return super().delete(request)


class RoleViews(ViewSet):
    model = Role
    serializer_class = RoleSerializers

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_all_role(self, request: Request):
        """获取全部角色"""
        items = Role.objects.only('id', 'name', 'description')
        data = []
        for i in items:
            data.append({'title': i.name,
                         'key': i.pk,
                         'description': i.description})
        return ResponseData.success(RESPONSE_MSG_0032, data)

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_permission(self, request: Request):
        """获取角色菜单与接口授权配置"""
        role_id = request.query_params.get('role_id')
        guest = Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists() if role_id else False
        authorization = RoleAuthorizationService.get(role_id)
        data = {
            'tree': [*PermissionMenuService.menu_tree(), fixed_endpoint_tree()],
            'menu_keys': sorted(key for key in PermissionMenuService.guest_permission_keys() if ':' not in key) if guest else (
                sorted(PermissionMenuService.menu_keys_from_authorization(authorization)) if role_id else []),
            'endpoint_groups': grouped_endpoint_catalog(),
            'endpoint_permissions': EndpointPermissionService.from_legacy_keys(PermissionMenuService.guest_permission_keys()) if guest else (
                EndpointPermissionService.from_authorization(authorization) if role_id else {}),
        }
        return ResponseData.success(RESPONSE_MSG_0205, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_permission(self, request: Request):
        """保存角色菜单与接口授权配置"""
        role_id = request.data.get('role_id')
        if Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists():
            return ResponseData.fail(RESPONSE_MSG_0215)
        saved = PermissionMenuService.save_role_permissions(
            role_id,
            request.data.get('menu_keys'),
            request.user.get('id') if isinstance(request.user, dict) else None,
            endpoint_permissions=request.data.get('endpoint_permissions'),
        )
        return ResponseData.success(RESPONSE_MSG_0206, saved)
