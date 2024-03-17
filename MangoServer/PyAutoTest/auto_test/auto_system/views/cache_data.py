# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import CacheData
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData
from PyAutoTest.tools.view_utils.response_msg import *


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


class CacheDataCRUD(ModelCRUD):
    model = CacheData
    queryset = CacheData.objects.all()
    serializer_class = CacheDataSerializersC
    serializer = CacheDataSerializers

    def get(self, request: Request):
        key_list = [{'describe': i.value, 'key': i.name} for i in CacheDataKeyEnum]
        for key in key_list:
            try:
                self.model.objects.get(key=key.get('key'))
            except self.model.DoesNotExist:
                for i, value in CacheDataKeyEnum.obj().items():
                    if i == key.get('key') and value:
                        key['value'] = value
                serializer = self.serializer(data=key)
                if serializer.is_valid():
                    serializer.save()
        books = self.model.objects.filter(key__in=CacheDataKeyEnum.get_key_list())
        return ResponseData.success(RESPONSE_MSG_0001,
                                    self.get_serializer_class()(instance=books, many=True).data,
                                    len(books))

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
