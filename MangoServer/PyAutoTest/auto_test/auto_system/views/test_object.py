# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enum_class.ui_enum import EnvironmentEnum, DevicePlatform
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.utils.view_utils.view_tools import enum_list


class TestObjectSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)
    executor_name = UserSerializers(read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectSerializersC(serializers.ModelSerializer):
    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializers
    serializer = TestObjectSerializersC


class TestObjectViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_environment_enum(self, request):
        """
         获取环境信息
         :param request:
         :return:
         """
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': enum_list(EnvironmentEnum)
        })

    @action(methods=['get'], detail=False)
    def get_platform_enum(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': enum_list(DevicePlatform)
        })

    @action(methods=['get'], detail=False)
    def get_test_obj_name(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TestObject.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': data
        })
