# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行记录视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.auto_test.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.auto_test.auto_data_factory.views.template import DataFactoryTemplateSerializerC
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.views.product_module import ProductModuleSerializersC
from src.auto_test.auto_system.views.test_object import TestObjectSerializersC
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryExecutionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        if obj.template_id and obj.template:
            return obj.template.name
        if obj.source_id:
            return f"{obj.source_type}#{obj.source_id}"
        return obj.source_type


class DataFactoryExecutionSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializersC(read_only=True)
    test_object = TestObjectSerializersC(read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        if obj.template_id and obj.template:
            return obj.template.name
        if obj.source_id:
            return f"{obj.source_type}#{obj.source_id}"
        return obj.source_type

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'module',
            'test_object',
            'test_object__project_product',
            'test_object__executor_name',
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__module',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
        )

class DataFactoryExecutionCRUD(ModelCRUD):
    model = DataFactoryExecution
    queryset = DataFactoryExecution.objects.all()
    serializer_class = DataFactoryExecutionSerializerC
    serializer = DataFactoryExecutionSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['template']

class DataFactoryExecutionViews(ViewSet):
    @action(methods=['get'], detail=False)
    @error_response('system')
    def detail_view(self, request: Request):
        from src.auto_test.auto_data_factory.views.execution_item import DataFactoryExecutionItemSerializerC

        execution = DataFactoryExecution.objects.select_related(
            'project_product',
            'module',
            'test_object',
            'template',
        ).get(id=request.query_params.get('execution_id'))
        items = DataFactoryExecutionItemSerializerC.setup_eager_loading(
            DataFactoryExecutionItem.objects.all()
        ).filter(execution=execution).order_by('cleanup_order', 'id')
        return ResponseData.success(RESPONSE_MSG_0001, {
            "execution": DataFactoryExecutionSerializerC(execution).data,
            "items": DataFactoryExecutionItemSerializerC(items, many=True).data,
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
        if result.get("already_cleaned"):
            return ResponseData.success((200, result.get("message") or "当前执行记录没有需要清理的数据"), result)
        return ResponseData.success(RESPONSE_MSG_0001, result)
