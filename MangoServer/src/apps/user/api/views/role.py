# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 角色表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.user.api.serializers.user import RoleSerializers
from src.apps.user.services.permission import GUEST_ROLE_NAME, PermissionMenuService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0032, RESPONSE_MSG_0205, RESPONSE_MSG_0206, RESPONSE_MSG_0215
from ...models import Role


class RoleCRUD(ModelCRUD):
    model = Role
    queryset = Role.objects.all()
    serializer_class = RoleSerializers
    serializer = RoleSerializers

    @staticmethod
    def is_guest_role_id(role_id):
        return Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists()

    @error_response('user')
    def put(self, request: Request):
        if self.is_guest_role_id(request.data.get('id')):
            return ResponseData.fail(RESPONSE_MSG_0215)
        return super().put(request)

    @error_response('user')
    def delete(self, request: Request):
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
        items = Role.objects.all()
        data = []
        for i in items:
            data.append({'title': i.name,
                         'key': i.pk,
                         'description': i.description})
        return ResponseData.success(RESPONSE_MSG_0032, data)

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_permission(self, request: Request):
        role_id = request.query_params.get('role_id')
        data = {
            'tree': PermissionMenuService.permission_tree(),
            'checked_keys': sorted(PermissionMenuService.role_permission_keys(role_id)) if role_id else []
        }
        return ResponseData.success(RESPONSE_MSG_0205, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_permission(self, request: Request):
        role_id = request.data.get('role_id')
        if Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists():
            return ResponseData.fail(RESPONSE_MSG_0215)
        permission_keys = request.data.get('permission_keys') or []
        checked_keys = PermissionMenuService.save_role_permissions(
            role_id,
            permission_keys,
            request.user.get('id') if isinstance(request.user, dict) else None,
        )
        return ResponseData.success(RESPONSE_MSG_0206, sorted(checked_keys))
