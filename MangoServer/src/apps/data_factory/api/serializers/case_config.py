# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂用例配置视图

from rest_framework import serializers

from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializerC
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryCaseConfigSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)
    case = serializers.IntegerField(source='source_id', read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
            'update_user',
        )
