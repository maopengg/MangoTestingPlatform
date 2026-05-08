# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据源绑定视图

from rest_framework import serializers

from src.auto_test.auto_data_factory.models import DataFactoryDatasourceBinding
from src.auto_test.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.auto_test.auto_system.views.database import DatabaseSerializersC
from src.auto_test.auto_system.views.test_object import TestObjectSerializersC
from src.tools.view.model_crud import ModelCRUD


class DataFactoryDatasourceBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryDatasourceBinding
        fields = '__all__'

    def validate(self, attrs):
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None
        )
        database = attrs.get('database', self.instance.database if self.instance else None)
        if datasource_alias and database and datasource_alias.db_type != database.db_type:
            raise serializers.ValidationError("逻辑数据源类型与实际数据库类型不一致")
        return attrs


class DataFactoryDatasourceBindingSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)
    test_object = TestObjectSerializersC(read_only=True)
    database = DatabaseSerializersC(read_only=True)

    class Meta:
        model = DataFactoryDatasourceBinding
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'datasource_alias',
            'datasource_alias__project_product',
            'datasource_alias__project_product__project',
            'test_object',
            'test_object__project_product',
            'test_object__executor_name',
            'database',
            'database__test_object',
            'database__test_object__project_product',
            'database__test_object__executor_name',
        )


class DataFactoryDatasourceBindingCRUD(ModelCRUD):
    model = DataFactoryDatasourceBinding
    queryset = DataFactoryDatasourceBinding.objects.all()
    serializer_class = DataFactoryDatasourceBindingSerializerC
    serializer = DataFactoryDatasourceBindingSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['datasource_alias', 'database']
