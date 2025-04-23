# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import json

from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_system.views.project import ProjectSerializers
from src.auto_test.auto_system.views.test_object import TestObjectSerializers
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import SystemEError, ERROR_MSG_0038
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class CacheDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = CacheData
        fields = '__all__'


class CacheDataSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)

    class Meta:
        model = CacheData
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'test_obj')
        return queryset


class CacheDataCRUD(ModelCRUD):
    model = CacheData
    queryset = CacheData.objects.all()
    serializer_class = CacheDataSerializersC
    serializer = CacheDataSerializers

    @error_response('system')
    def get(self, request: Request):
        books = self.model.objects.filter(key__in=CacheDataKeyEnum.get_key_list())
        try:
            return ResponseData.success(RESPONSE_MSG_0001,
                                        self.serializer_class(instance=self.serializer_class.setup_eager_loading(books),
                                                              many=True).data,
                                        books.count())
        except FieldError:
            return ResponseData.success(RESPONSE_MSG_0001,
                                        self.serializer_class(instance=books,
                                                              many=True).data,
                                        books.count())

    @error_response('system')
    def put(self, request: Request):
        for i in request.data:
            serializer = self.serializer(
                instance=self.model.objects.get(pk=i.get('id')),
                data=i
            )
            if serializer.is_valid():
                serializer.save()
            else:
                return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)
        return ResponseData.success(RESPONSE_MSG_0082, )


class CacheDataViews(ViewSet):
    model = CacheData
    serializer_class = CacheDataSerializers

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def get_key_value(self, request: Request):
        """
        上传文件
        @param request:
        @return:
        """
        try:
            model = self.model.objects.get(key=request.query_params.get('key'))
        except CacheData.DoesNotExist:
            raise SystemEError(*ERROR_MSG_0038)
        return ResponseData.success(RESPONSE_MSG_0031, json.loads(model.value))
