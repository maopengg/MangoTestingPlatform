# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据源绑定视图

from rest_framework import serializers
from rest_framework.request import Request

from src.apps.auto_data_factory.models import DataFactoryDatasourceBinding
from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.auto_system.views.database import DatabaseSerializersC
from src.common.exceptions import ToolsError
from src.common.tools.decorator.error_response import error_response
from src.apps.auto_system.views.test_object import TestObjectSerializersC
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0002, RESPONSE_MSG_0082, RESPONSE_MSG_0116


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
        test_object = attrs.get('test_object', self.instance.test_object if self.instance else None)
        database = attrs.get('database', self.instance.database if self.instance else None)
        if datasource_alias and database and datasource_alias.db_type != database.db_type:
            raise serializers.ValidationError("逻辑数据源类型与实际数据库类型不一致")
        if datasource_alias and test_object and datasource_alias.project_product_id != test_object.project_product_id:
            raise serializers.ValidationError("测试环境不属于当前逻辑数据源的项目/产品")
        if test_object and database and database.test_object_id != test_object.id:
            raise serializers.ValidationError("实际数据库不属于当前测试环境")
        if datasource_alias and test_object and database:
            existing_binding = DataFactoryDatasourceBinding.objects.filter(
                datasource_alias=datasource_alias,
                test_object=test_object,
            ).first()
            if existing_binding and existing_binding.database_id != database.id:
                raise serializers.ValidationError("当前逻辑数据源已绑定其他真实数据库，一个逻辑数据源在同一测试环境下只能绑定一个真实数据库")
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

    @error_response('system')
    def post(self, request: Request):
        instance = self.get_existing_binding(request.data)
        serializer = self.serializer(
            instance=instance,
            data=request.data,
            partial=bool(instance),
        )
        if serializer.is_valid():
            serializer.save()
            message = RESPONSE_MSG_0082 if instance else RESPONSE_MSG_0002
            return ResponseData.success(message, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0116, serializer.errors)

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        instance = cls.get_existing_binding(data)
        serializer = cls.serializer(instance=instance, data=data, partial=bool(instance))
        if serializer.is_valid():
            serializer.save()
            return dict(serializer.data)
        raise ToolsError(*RESPONSE_MSG_0116, value=(serializer.errors,))

    @classmethod
    def get_existing_binding(cls, data):
        datasource_alias = data.get('datasource_alias')
        test_object = data.get('test_object')
        if not datasource_alias or not test_object:
            return None
        return cls.model.objects.filter(
            datasource_alias_id=datasource_alias,
            test_object_id=test_object,
        ).first()
