# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.system_enum import EnvironmentEnum, DevicePlatformEnum, AutoTestTypeEnum
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery
from PyAutoTest.tools.view_utils.view_tools import enum_list


class TestObjectSerializers(serializers.ModelSerializer):
    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    executor_name = UserSerializers(read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializersC
    serializer = TestObjectSerializers


class TestObjectQuery(ModelQuery):
    """
    条件查
    """
    model = TestObject
    serializer_class = TestObjectSerializersC


class TestObjectViews(ViewSet):
    model = TestObject
    serializer_class = TestObjectSerializers

    @action(methods=['get'], detail=False)
    def get_environment_enum(self, request: Request):
        """
         获取环境信息
         :param request:
         :return:
         """
        return ResponseData.success('获取数据成功', enum_list(EnvironmentEnum))

    @action(methods=['get'], detail=False)
    def get_platform_enum(self, request: Request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        return ResponseData.success('获取数据成功', enum_list(DevicePlatformEnum))

    @action(methods=['get'], detail=False)
    def get_auto_test_enum(self, request: Request):
        """
         获取环境信息
         :param request:
         :return:
         """
        return ResponseData.success('获取数据成功', enum_list(AutoTestTypeEnum))

    @action(methods=['get'], detail=False)
    def get_test_obj_name(self, request: Request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TestObject.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)
