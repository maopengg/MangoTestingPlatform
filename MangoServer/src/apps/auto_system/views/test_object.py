# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_system.models import TestObject
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_system.service.factory import get_enabled_databases
from src.apps.auto_user.views.user import UserSerializers
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import MangoServerError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


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
                if not get_enabled_databases(request.data.get('id')).exists():
                    return ResponseData.fail(RESPONSE_MSG_0123)
            if db_c_status is not None:
                obj.db_c_status = db_c_status
            if db_rud_status is not None:
                obj.db_rud_status = db_rud_status
            obj.save()
            return ResponseData.success(RESPONSE_MSG_0096)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
