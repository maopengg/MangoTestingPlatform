# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据库绑定视图

from mangotools.enums import StatusEnum
from rest_framework import serializers

from src.apps.data_factory.api.serializers.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID, DataFactoryError
from src.apps.data_factory.models import DataFactoryDatasourceBinding
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.formatters.related import format_data_source
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryDatasourceBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryDatasourceBinding
        fields = '__all__'

    def to_internal_value(self, data):
        payload = data.copy()
        if payload.get('data_source') and not payload.get('database'):
            payload['database'] = payload['data_source']
        payload.pop('data_source', None)
        return super().to_internal_value(payload)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['data_source'] = data.get('database')
        return data

    def validate(self, attrs):
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None
        )
        environment = attrs.get('environment', self.instance.environment if self.instance else None)
        database = attrs.get('database', self.instance.database if self.instance else None)
        if datasource_alias and database:
            if datasource_alias.source_category != database.source_category:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("逻辑数据库分类与实际数据库分类不一致",))
            if datasource_alias.db_type != database.db_type:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("逻辑数据库类型与实际数据库类型不一致",))
            DatasourceTargetService.validate(database, *[
                attrs.get(key, getattr(self.instance, key) if self.instance else default)
                for key, default in [('database_name', ''), ('schema_name', ''), ('redis_db', None)]
            ])
        db_rud_status = attrs.get(
            'db_rud_status',
            self.instance.db_rud_status if self.instance else StatusEnum.FAIL.value,
        )
        if environment == EnvironmentEnum.PRO.value and db_rud_status == StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("生产环境数据库禁止开启增删改权限",))
        return attrs


class DataFactoryDatasourceBindingSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)
    database = RelatedObjectField(formatter=format_data_source, read_only=True)
    data_source = RelatedObjectField(formatter=format_data_source, source='database', read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryDatasourceBinding
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'datasource_alias',
            'datasource_alias__project_product',
            'datasource_alias__project_product__project',
            'database',
            'update_user',
        )
