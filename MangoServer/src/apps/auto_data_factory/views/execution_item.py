# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行明细视图

from rest_framework import serializers

from src.apps.auto_data_factory.models import DataFactoryExecutionItem
from src.apps.auto_data_factory.views.execution import DataFactoryExecutionSerializerC
from src.apps.auto_data_factory.views.template import DataFactoryTemplateSerializerC
from src.apps.auto_system.views.database import DatabaseSerializersC
from src.common.tools.view.model_crud import ModelCRUD


class DataFactoryExecutionItemSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryExecutionItem
        fields = '__all__'


class DataFactoryExecutionItemSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    execution = DataFactoryExecutionSerializerC(read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)
    database = DatabaseSerializersC(read_only=True)

    class Meta:
        model = DataFactoryExecutionItem
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'execution',
            'execution__project_product',
            'execution__project_product__project',
            'execution__template',
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
            'template__entity__datasource_alias__project_product__project',
            'database',
            'database__test_object',
            'database__test_object__project_product',
            'database__test_object__executor_name',
        )


class DataFactoryExecutionItemCRUD(ModelCRUD):
    model = DataFactoryExecutionItem
    queryset = DataFactoryExecutionItem.objects.all()
    serializer_class = DataFactoryExecutionItemSerializerC
    serializer = DataFactoryExecutionItemSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['execution', 'template', 'database']
