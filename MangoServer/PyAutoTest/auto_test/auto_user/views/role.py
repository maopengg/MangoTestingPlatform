# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 角色表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import RESPONSE_MSG_0032
from ..models import Role


class RoleSerializers(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset


class RoleCRUD(ModelCRUD):
    model = Role
    queryset = Role.objects.all()
    serializer_class = RoleSerializers
    serializer = RoleSerializers


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
                         'key': i.pk})
        return ResponseData.success(RESPONSE_MSG_0032, data)
