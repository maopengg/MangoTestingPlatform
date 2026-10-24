# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.exceptions import (
    API_PROJECT_PRODUCT_TYPE_VARIABLE_DUPLICATED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiPublic
from src.apps.data_factory.formatters import format_datasource_alias
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.common.utils.environment_scope import normalize_test_envs, sync_test_env_attrs, test_envs_titles
from src.common.validators.serializer_fields import RelatedObjectField


class ApiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'

    def validate_type(self, value):
        if value not in ApiPublicTypeEnum.get_key_list():
            raise serializers.ValidationError('公共变量类型只支持自定义、SQL和代码变量')
        return value

    def validate(self, attrs):
        sync_test_env_attrs(attrs, self.instance)
        public_type = attrs.get('type', self.instance.type if self.instance else None)
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None,
        )
        project_product = attrs.get(
            'project_product',
            self.instance.project_product if self.instance else None,
        )
        if public_type == ApiPublicTypeEnum.SQL.value:
            DataFactoryDatasourceResolver.require_sql_public_alias(
                datasource_alias,
                project_product.id if project_product else None,
            )
        else:
            attrs['datasource_alias'] = None
        if self.instance is None:
            key = attrs.get('key')
            value = attrs.get('value')
            test_envs = sorted(normalize_test_envs(attrs.get('test_envs')))
            candidates = ApiPublic.objects.filter(
                project_product=project_product,
                type=public_type,
                key=key,
                value=value,
            ).only('id', 'key', 'value', 'test_envs')
            duplicate = next(
                (
                    item
                    for item in candidates
                    if item.key == key
                       and item.value == value
                       and sorted(normalize_test_envs(item.test_envs)) == test_envs
                ),
                None,
            )
            if duplicate:
                raise AutoApiError(API_PROJECT_PRODUCT_TYPE_VARIABLE_DUPLICATED, value=(duplicate.id,))
        return attrs


class ApiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    datasource_alias = RelatedObjectField(formatter=format_datasource_alias, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['test_env_titles'] = test_envs_titles(data.get('test_envs') or [], EnvironmentEnum)
        return data

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'datasource_alias',
            'update_user')
        return queryset
