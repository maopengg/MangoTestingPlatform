# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from django.core.exceptions import FieldError
from django.db import ProgrammingError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_system.models import CacheData
from src.apps.auto_system.service.system_config import CONFIG_GROUP_TITLES, SystemConfigService
from src.apps.auto_system.views.project import ProjectSerializers
from src.apps.auto_system.views.test_object import TestObjectSerializers
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


SECRET_VALUE_MASK = "__KEEP_SECRET__"


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
        SystemConfigService.sync_registered_configs()
        books = self.model.objects.filter(is_public=True, is_enabled=True).order_by('group', 'sort', 'id')
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
            cache_data = self.__get_config(i)
            data = {
                **self.serializer(instance=cache_data).data,
                **i,
            }
            if cache_data.is_secret and i.get('value') == SECRET_VALUE_MASK:
                data['value'] = cache_data.value
            serializer = self.serializer(instance=cache_data, data=data)
            if serializer.is_valid():
                serializer.save()
                SystemConfigService.invalidate(cache_data.key)
            else:
                return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)
        return ResponseData.success(RESPONSE_MSG_0082, )

    @staticmethod
    def __get_config(data):
        if data.get('id'):
            return CacheData.objects.get(pk=data.get('id'))
        return CacheData.objects.get(key=data.get('key'))


class CacheDataViews(ViewSet):
    model = CacheData
    serializer_class = CacheDataSerializers

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def grouped(self, request: Request):
        SystemConfigService.sync_registered_configs()
        queryset = self.model.objects.filter(is_public=True, is_enabled=True).order_by('group', 'sort', 'id')
        grouped_data = {}
        for item in queryset:
            group_key = item.group or 'system'
            grouped_data.setdefault(group_key, {
                'key': group_key,
                'title': CONFIG_GROUP_TITLES.get(group_key, group_key),
                'items': [],
            })
            grouped_data[group_key]['items'].append(self.__serialize_item(item))
        data = list(grouped_data.values())
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def get_key_value(self, request: Request):
        """
        上传文件
        @param request:
        @return:
        """
        try:
            value = SystemConfigService.get(request.query_params.get('key'))
        except ProgrammingError:
            return ResponseData.fail(RESPONSE_MSG_0141)
        return ResponseData.success(RESPONSE_MSG_0031, value)

    @staticmethod
    def __serialize_item(item):
        data = CacheDataSerializers(instance=item).data
        data['has_value'] = item.value not in (None, '')
        if item.is_secret:
            data['value'] = SECRET_VALUE_MASK if data['has_value'] else None
        return data
