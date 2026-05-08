# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂实体视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_data_factory.models import DataFactoryEntity
from src.auto_test.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.auto_test.auto_system.views.database import DatabaseSerializersC
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.exceptions import ToolsError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryEntitySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None
        )
        if not datasource_alias:
            raise serializers.ValidationError("工厂实体必须绑定逻辑数据源")
        project_product = attrs.get(
            'project_product',
            self.instance.project_product if self.instance else None
        )
        table_name = attrs.get('table_name', self.instance.table_name if self.instance else None)
        if not table_name:
            raise serializers.ValidationError("工厂实体必须绑定表名")
        if project_product and datasource_alias and table_name:
            queryset = DataFactoryEntity.objects.filter(
                project_product=project_product,
                datasource_alias=datasource_alias,
                table_name=table_name,
            )
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError(f"当前逻辑数据源下已存在表实体：{table_name}")
        return attrs


class DataFactoryEntitySerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    database = DatabaseSerializersC(read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'database',
            'database__test_object',
            'database__test_object__project_product',
            'database__test_object__executor_name',
            'datasource_alias',
            'datasource_alias__project_product',
        )


class DataFactoryEntityCRUD(ModelCRUD):
    model = DataFactoryEntity
    queryset = DataFactoryEntity.objects.all()
    serializer_class = DataFactoryEntitySerializerC
    serializer = DataFactoryEntitySerializer
    not_matching_str = ModelCRUD.not_matching_str + ['datasource_alias']

    def post(self, request: Request):
        duplicated = self.get_duplicated_entity(request.data)
        if duplicated:
            return ResponseData.fail((300, f"当前逻辑数据源下已存在表实体：{duplicated.table_name}，请编辑已有实体"))
        return super().post(request)

    def put(self, request: Request):
        duplicated = self.get_duplicated_entity(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail((300, f"当前逻辑数据源下已存在表实体：{duplicated.table_name}，请编辑已有实体"))
        return super().put(request)

    @staticmethod
    def get_duplicated_entity(data: dict, exclude_id=None):
        project_product = data.get('project_product')
        datasource_alias = data.get('datasource_alias')
        table_name = data.get('table_name')
        if not project_product or not datasource_alias or not table_name:
            return None
        queryset = DataFactoryEntity.objects.filter(
            project_product_id=project_product,
            datasource_alias_id=datasource_alias,
            table_name=table_name,
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()


class DataFactoryEntityViews(ViewSet):
    @action(methods=['post'], detail=False)
    @error_response('system')
    def copy(self, request: Request):
        raise ToolsError(300, "实体是表级定义，同一逻辑数据源下同一张表只需要维护一个实体，不支持复制")

    @action(methods=['put'], detail=False)
    @error_response('system')
    def status(self, request: Request):
        entity = DataFactoryEntity.objects.get(id=request.data.get('id'))
        if request.data.get('status') is None:
            raise ToolsError(300, "状态不能为空")
        entity.status = request.data.get('status')
        entity.save(update_fields=['status', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryEntitySerializer(entity).data)
