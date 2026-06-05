# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂实体视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from django.db import transaction

from src.apps.auto_data_factory.models import DataFactoryEntity
from src.apps.auto_system.models import ProductModule
from src.apps.auto_data_factory.service.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.auto_data_factory.service.discover import DataFactoryDiscover
from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasSerializerC
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_system.views.product_module import ProductModuleSerializersC
from src.common.enums.data_factory_enum import DataFactoryOperationTypeEnum
from src.common.exceptions import ToolsError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryEntitySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'
        validators = []

    def validate(self, attrs):
        attrs['create_type'] = DataFactoryOperationTypeEnum.SQL.value
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
        module = attrs.get('module', self.instance.module if self.instance else None)
        if not module:
            raise serializers.ValidationError("工厂实体必须绑定模块")
        if project_product and module and module.project_product_id != project_product.id:
            raise serializers.ValidationError("模块不属于当前项目/产品")
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
    module = ProductModuleSerializersC(read_only=True)
    datasource_alias = DataFactoryDatasourceAliasSerializerC(read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'module',
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
    def batch_generate(self, request: Request):
        project_product = request.data.get('project_product')
        module = request.data.get('module')
        datasource_alias = request.data.get('datasource_alias')
        test_env = request.data.get('test_env')
        tables = request.data.get('tables') or []
        sync_fields = request.data.get('sync_fields', True)
        skip_exists = request.data.get('skip_exists', True)

        if not project_product:
            raise ToolsError(300, "产品不能为空")
        if not module:
            raise ToolsError(300, "模块不能为空")
        if not ProductModule.objects.filter(id=module, project_product_id=project_product).exists():
            raise ToolsError(300, "模块不属于当前项目/产品")
        if not datasource_alias:
            raise ToolsError(300, "逻辑数据源不能为空")
        if is_missing_value(test_env):
            raise ToolsError(300, "请先在顶部选择测试环境")
        if not isinstance(tables, list) or not tables:
            raise ToolsError(300, "请至少选择一张表")

        database = DataFactoryDatasourceResolver.resolve_alias_by_env(
            datasource_alias,
            project_product,
            test_env,
        )
        test_object_id = DataFactoryDatasourceResolver.resolve_test_object_id(project_product, test_env)
        DataFactoryDatasourceResolver.require_permission(test_object_id, write=False)
        result_items = []
        success = 0
        skipped = 0
        failed = 0

        for table in tables:
            table_name = table.get('table_name') or table.get('name')
            entity_name = table.get('name') or table.get('table_comment') or table_name
            if not table_name or not entity_name:
                failed += 1
                result_items.append({
                    "table_name": table_name,
                    "name": entity_name,
                    "status": "failed",
                    "entity_id": None,
                    "field_count": 0,
                    "message": "表名和实体名称不能为空",
                })
                continue

            duplicated = DataFactoryEntity.objects.filter(
                project_product_id=project_product,
                datasource_alias_id=datasource_alias,
                table_name=table_name,
            ).first()
            if duplicated:
                if skip_exists:
                    skipped += 1
                    result_items.append({
                        "table_name": table_name,
                        "name": duplicated.name,
                        "status": "skipped",
                        "entity_id": duplicated.id,
                        "field_count": 0,
                        "message": "当前逻辑数据源下已存在实体",
                    })
                    continue
                failed += 1
                result_items.append({
                    "table_name": table_name,
                    "name": entity_name,
                    "status": "failed",
                    "entity_id": duplicated.id,
                    "field_count": 0,
                    "message": "当前逻辑数据源下已存在实体",
                })
                continue

            try:
                schema = DataFactoryDiscover.get_table_schema(database, table_name)
                unique_key = ""
                for index in schema.get("indexes") or []:
                    column_names = index.get("column_names") or []
                    if index.get("unique") and len(column_names) == 1:
                        unique_key = column_names[0]
                        break

                with transaction.atomic():
                    entity = DataFactoryEntity.objects.create(
                        project_product_id=project_product,
                        module_id=module,
                        datasource_alias_id=datasource_alias,
                        name=entity_name,
                        table_name=table_name,
                        primary_key=(schema.get("primary_keys") or ["id"])[0],
                        unique_key=unique_key,
                        cleanup_order=100,
                    )
                    field_count = 0
                    if sync_fields:
                        from src.apps.auto_data_factory.views.field import DataFactoryFieldViews

                        saved_fields = DataFactoryFieldViews.save_schema_fields(
                            entity,
                            schema.get("columns") or [],
                            replace=True,
                        )
                        field_count = len(saved_fields)

                success += 1
                result_items.append({
                    "table_name": table_name,
                    "name": entity.name,
                    "status": "success",
                    "entity_id": entity.id,
                    "field_count": field_count,
                    "message": "生成成功",
                })
            except Exception as error:
                failed += 1
                result_items.append({
                    "table_name": table_name,
                    "name": entity_name,
                    "status": "failed",
                    "entity_id": None,
                    "field_count": 0,
                    "message": str(error),
                })

        return ResponseData.success(RESPONSE_MSG_0001, {
            "success": success,
            "skipped": skipped,
            "failed": failed,
            "items": result_items,
        }, len(result_items))

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
