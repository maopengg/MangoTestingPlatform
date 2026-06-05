# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-10-12 18:14
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_system.models import ProductModule
from src.apps.auto_system.views.project_product import ProjectProductSerializers
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ProductModuleSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ProductModule
        fields = '__all__'


class ProductModuleSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializers(read_only=True)

    class Meta:
        model = ProductModule
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product')
        return queryset


class ProductModuleCRUD(ModelCRUD):
    model = ProductModule
    queryset = ProductModule.objects.all()
    serializer_class = ProductModuleSerializersC
    # post专用序列化器
    serializer = ProductModuleSerializers


class ProductModuleViews(ViewSet):
    model = ProductModule
    serializer_class = ProductModuleSerializers

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def get_module_name(self, request: Request):
        """
        模块的ID和name
        @param request:
        @return:
        """
        project_product_id = request.query_params.get('project_product_id')
        queryset = self.model.objects.values(
            'id',
            'name',
            'superior_module_1',
            'superior_module_2',
        )
        if project_product_id:
            queryset = queryset.filter(project_product=project_product_id)
        data = [
            {
                'key': item['id'],
                'title': item['name'],
                'superior_module_1': item['superior_module_1'],
                'superior_module_2': item['superior_module_2'],
            }
            for item in queryset
        ]
        return ResponseData.success(RESPONSE_MSG_0031, data)
