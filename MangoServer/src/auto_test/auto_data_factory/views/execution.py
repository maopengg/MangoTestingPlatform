# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行记录视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.auto_test.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryExecutionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'


class DataFactoryExecutionItemSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryExecutionItem
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('execution', 'entity', 'template', 'database')


class DataFactoryExecutionSerializerC(DataFactoryExecutionSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'test_object', 'template')


class DataFactoryExecutionCRUD(ModelCRUD):
    model = DataFactoryExecution
    queryset = DataFactoryExecution.objects.all()
    serializer_class = DataFactoryExecutionSerializerC
    serializer = DataFactoryExecutionSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['template']


class DataFactoryExecutionItemCRUD(ModelCRUD):
    model = DataFactoryExecutionItem
    queryset = DataFactoryExecutionItem.objects.all()
    serializer_class = DataFactoryExecutionItemSerializer
    serializer = DataFactoryExecutionItemSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['execution', 'entity', 'template', 'database']


class DataFactoryExecutionViews(ViewSet):
    @action(methods=['get'], detail=False)
    @error_response('system')
    def detail(self, request: Request):
        execution = DataFactoryExecution.objects.select_related(
            'project_product',
            'test_object',
            'template',
        ).get(id=request.query_params.get('execution_id'))
        items = DataFactoryExecutionItem.objects.filter(execution=execution).order_by('cleanup_order', 'id')
        return ResponseData.success(RESPONSE_MSG_0001, {
            "execution": DataFactoryExecutionSerializer(execution).data,
            "items": DataFactoryExecutionItemSerializer(items, many=True).data,
            "context": execution.context,
        })

    @action(methods=['get'], detail=False)
    @error_response('system')
    def context(self, request: Request):
        execution = DataFactoryExecution.objects.get(id=request.query_params.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0001, execution.context)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def cleanup(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution(request.data.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def cleanup_retry(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution(request.data.get('execution_id'))
        return ResponseData.success(RESPONSE_MSG_0001, result)
