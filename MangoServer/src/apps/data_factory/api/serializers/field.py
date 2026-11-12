# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段规则视图

from rest_framework import serializers

from src.apps.data_factory.api.serializers.entity import DataFactoryEntitySerializerC
from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.models import DataFactoryField
from src.apps.data_factory.services.assets.field import DataFactoryFieldService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryFieldSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    entity = DataFactoryEntitySerializerC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryField
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("generator_type") == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            config = data.get("generator_config") or {}
            data["generator_config"] = DataFactoryFieldService.normalize_dependency_config(config)
        return data

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'entity',
            'entity__project_product',
            'entity__project_product__project',
            'entity__datasource_alias',
            'entity__datasource_alias__project_product',
            'entity__datasource_alias__project_product__project',
            'update_user',
        )
