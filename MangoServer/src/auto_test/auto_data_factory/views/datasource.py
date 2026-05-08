# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据源视图

from rest_framework import serializers
from rest_framework.request import Request

from src.auto_test.auto_data_factory.models import (
    DataFactoryDatasourceAlias,
    DataFactoryDatasourceBinding,
)
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData


class DataFactoryDatasourceAliasSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryDatasourceAlias
        fields = '__all__'
        validators = []


class DataFactoryDatasourceAliasSerializerC(DataFactoryDatasourceAliasSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product')


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


class DataFactoryDatasourceBindingSerializerC(DataFactoryDatasourceBindingSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('datasource_alias', 'test_object', 'database')


class DataFactoryDatasourceAliasCRUD(ModelCRUD):
    model = DataFactoryDatasourceAlias
    queryset = DataFactoryDatasourceAlias.objects.all()
    serializer_class = DataFactoryDatasourceAliasSerializerC
    serializer = DataFactoryDatasourceAliasSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['db_type']

    def post(self, request: Request):
        duplicated = self.get_duplicated_code(request.data)
        if duplicated:
            return ResponseData.fail((300, f"当前产品下已存在逻辑数据源编码：{duplicated.code}，请编辑已有数据源或更换编码"))
        return super().post(request)

    def put(self, request: Request):
        duplicated = self.get_duplicated_code(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail((300, f"当前产品下已存在逻辑数据源编码：{duplicated.code}，请编辑已有数据源或更换编码"))
        return super().put(request)

    @staticmethod
    def get_duplicated_code(data: dict, exclude_id=None):
        project_product = data.get('project_product')
        code = data.get('code')
        if not project_product or not code:
            return None
        queryset = DataFactoryDatasourceAlias.objects.filter(project_product_id=project_product, code=code)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()


class DataFactoryDatasourceBindingCRUD(ModelCRUD):
    model = DataFactoryDatasourceBinding
    queryset = DataFactoryDatasourceBinding.objects.all()
    serializer_class = DataFactoryDatasourceBindingSerializerC
    serializer = DataFactoryDatasourceBindingSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['datasource_alias', 'database']
