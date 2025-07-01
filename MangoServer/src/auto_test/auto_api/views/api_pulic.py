# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiPublic
from src.auto_test.auto_system.models import Database
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.api_enum import ApiPublicTypeEnum
from src.enums.tools_enum import StatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class ApiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'


class ApiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product')
        return queryset


class ApiPublicCRUD(ModelCRUD):
    model = ApiPublic
    queryset = ApiPublic.objects.all()
    serializer_class = ApiPublicSerializersC
    serializer = ApiPublicSerializers


class ApiPublicViews(ViewSet):
    model = ApiPublic
    serializer_class = ApiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0104, )

