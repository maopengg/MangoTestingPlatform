# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.data_factory.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializerC
from src.apps.data_factory.models import DataFactoryExecution
from src.apps.data_factory.selectors.execution import format_execution_source_info
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryExecutionSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    source_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        return format_execution_source_info(obj).get("display")

    @staticmethod
    def get_source_info(obj):
        return format_execution_source_info(obj)


class DataFactoryExecutionSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    source_display = serializers.SerializerMethodField(read_only=True)
    source_info = serializers.SerializerMethodField(read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)

    class Meta:
        model = DataFactoryExecution
        fields = '__all__'

    @staticmethod
    def get_source_display(obj):
        return format_execution_source_info(obj).get("display")

    @staticmethod
    def get_source_info(obj):
        return format_execution_source_info(obj)

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(ProductModuleService.with_full_paths(
            queryset,
            'module',
            'template__module',
            'template__entity__module',
        ).select_related(
            'project_product',
            'project_product__project',
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__module',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
        ))


class DataFactoryExecutionBatchCleanupSerializer(serializers.Serializer):
    """执行记录批量清理入参。"""

    execution_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=100,
    )

    def validate_execution_ids(self, value):
        return list(dict.fromkeys(value))
