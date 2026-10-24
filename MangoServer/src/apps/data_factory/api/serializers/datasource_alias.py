# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据库视图

from rest_framework import serializers

from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryDatasourceAliasSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryDatasourceAlias
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        source_category = attrs.get(
            'source_category',
            self.instance.source_category if self.instance else DataSourceCategoryEnum.DATABASE.value,
        )
        source_type = attrs.get('db_type', self.instance.db_type if self.instance else None)
        if DataSourceTypeEnum.category(source_type) != source_category:
            raise serializers.ValidationError("数据库分类与具体类型不匹配")
        return attrs


class DataFactoryDatasourceAliasSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryDatasourceAlias
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'project_product__project', 'update_user')
