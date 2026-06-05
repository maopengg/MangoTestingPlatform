# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_data_factory.service.datasource import DataFactoryDatasource
from src.apps.auto_system.models import Database
from src.apps.auto_system.views.test_object import TestObjectSerializersC
from src.common.enums.tools_enum import StatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class DatabaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Database
        fields = '__all__'


class DatabaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    test_object = TestObjectSerializersC(read_only=True)

    class Meta:
        model = Database
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'test_object',
        )
        return queryset


class DatabaseCRUD(ModelCRUD):
    model = Database
    queryset = Database.objects.all()
    serializer_class = DatabaseSerializersC
    serializer = DatabaseSerializers


class DatabaseViews(ViewSet):
    model = Database
    serializer_class = DatabaseSerializers

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0047, )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def test(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('id'))
        try:
            DataFactoryDatasource.test_connection(obj)
        except Exception:
            return ResponseData.fail(RESPONSE_MSG_0123, )
        return ResponseData.success(RESPONSE_MSG_0127, )
