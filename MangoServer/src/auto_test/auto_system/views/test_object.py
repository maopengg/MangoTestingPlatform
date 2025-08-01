# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.models import TestObject
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.service.factory import func_mysql_config
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.tools_enum import StatusEnum
from src.exceptions import MangoServerError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class TestObjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    executor_name = UserSerializers(read_only=True)

    class Meta:
        model = TestObject
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'executor_name')
        return queryset


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializersC
    serializer = TestObjectSerializers


class TestObjectViews(ViewSet):
    model = TestObject
    serializer_class = TestObjectSerializers

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        db_c_status = request.data.get('db_c_status')
        db_rud_status = request.data.get('db_rud_status')
        try:
            obj = self.model.objects.get(id=request.data.get('id'))
            if db_c_status == StatusEnum.SUCCESS.value or db_rud_status == StatusEnum.SUCCESS.value:
                func_mysql_config(request.data.get('id'))
            if db_c_status is not None:
                obj.db_c_status = db_c_status
            if db_rud_status is not None:
                obj.db_rud_status = db_rud_status
            obj.save()
            return ResponseData.success(RESPONSE_MSG_0096)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
