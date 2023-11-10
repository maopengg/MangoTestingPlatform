# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 角色表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from ..models import Role


class RoleSerializers(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'  # 全部进行序列化


class RoleCRUD(ModelCRUD):
    model = Role
    queryset = Role.objects.all()
    serializer_class = RoleSerializers
    serializer = RoleSerializers


class RoleViews(ViewSet):
    model = Role
    serializer_class = RoleSerializers

    @action(methods=['get'], detail=False)
    def get_all_role(self, request: Request):
        items = Role.objects.all()
        data = []
        for i in items:
            data.append({'title': i.name,
                         'key': i.pk})
        return ResponseData.success('获取所有角色成功', data)
