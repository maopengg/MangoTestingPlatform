# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段规则视图

from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_data_factory.models import DataFactoryEntity, DataFactoryField
from src.apps.auto_data_factory.service.generator import DataFactoryValueGenerator
from src.apps.auto_data_factory.service.runtime_cache import DataFactoryRuntimeCache
from src.apps.auto_data_factory.service.type_cast import DataFactoryTypeCast
from src.apps.auto_data_factory.views.entity import DataFactoryEntitySerializerC
from src.common.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.common.exceptions import ToolsError
from src.common.models.data_factory_model import validate_data_factory_generator_config
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryFieldSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryField
        fields = '__all__'

    def validate(self, attrs):
        generator_type = attrs.get(
            'generator_type',
            self.instance.generator_type if self.instance else None
        )
        generator_config = attrs.get(
            'generator_config',
            self.instance.generator_config if self.instance else {}
        ) or {}
        enum_values = attrs.get(
            'enum_values',
            self.instance.enum_values if self.instance else []
        ) or []

        try:
            attrs["generator_config"] = validate_data_factory_generator_config(
                generator_type,
                generator_config,
                allow_dependency_template=False,
            )
        except (TypeError, ValueError) as error:
            raise serializers.ValidationError(f"生成配置格式错误：{error}") from error

        generator_config = attrs["generator_config"]

        if generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = generator_config.get("values") or enum_values
            if not values:
                raise serializers.ValidationError("枚举生成器必须配置 values 或字段 enum_values")
            if "value" in generator_config and generator_config["value"] not in values:
                raise serializers.ValidationError("枚举固定值必须在 values 范围内")

        return attrs


class DataFactoryFieldSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    entity = DataFactoryEntitySerializerC(read_only=True)

    class Meta:
        model = DataFactoryField
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("generator_type") == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            config = data.get("generator_config") or {}
            data["generator_config"] = DataFactoryFieldViews.normalize_dependency_config(config)
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
        )


class DataFactoryFieldCRUD(ModelCRUD):
    model = DataFactoryField
    queryset = DataFactoryField.objects.all()
    serializer_class = DataFactoryFieldSerializerC
    serializer = DataFactoryFieldSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['entity']

    @error_response('system')
    def get(self, request: Request):
        queryset = DataFactoryFieldSerializerC.setup_eager_loading(DataFactoryField.objects.all())
        entity_id = request.query_params.get('entity')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__contains=name)

        queryset = queryset.order_by('sort', 'id')
        page_size = request.query_params.get("pageSize")
        page = request.query_params.get("page")
        if page_size and page:
            data_list, count = self.paging_list(
                page_size,
                page,
                queryset,
                DataFactoryFieldSerializerC,
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DataFactoryFieldSerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class DataFactoryFieldViews(ViewSet):
    @staticmethod
    def save_schema_fields(entity: DataFactoryEntity, columns: list, replace: bool = True) -> list:
        saved_fields = []
        field_names = []
        for index, column in enumerate(columns):
            recommend = column.get("recommend", {}) or {}
            instance = DataFactoryField.objects.filter(entity=entity, name=column.get("name")).first()
            field_data = {
                **column,
                "entity": entity.id,
                "generator_type": (
                    column["generator_type"]
                    if "generator_type" in column
                    else instance.generator_type if instance else recommend.get("generator_type", 1)
                ),
                "generator_config": (
                    column["generator_config"]
                    if "generator_config" in column
                    else instance.generator_config if instance else recommend.get("generator_config", {})
                ),
                "sort": column.get("sort", index),
            }
            if not field_data.get("name"):
                raise ToolsError(300, "字段 name 不能为空")
            DataFactoryFieldViews.normalize_field_data(field_data)
            field_names.append(field_data["name"])
            serializer = DataFactoryFieldSerializer(instance=instance, data=field_data, partial=bool(instance))
            serializer.is_valid(raise_exception=True)
            serializer.save()
            saved_fields.append(serializer.data)

        if replace:
            DataFactoryField.objects.filter(entity=entity).exclude(name__in=field_names).delete()
        return saved_fields

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_save(self, request: Request):
        entity_id = request.data.get('entity_id')
        fields = request.data.get('fields') or []
        replace = request.data.get('replace', False)
        if not entity_id:
            raise ToolsError(300, "entity_id 不能为空")
        if not isinstance(fields, list):
            raise ToolsError(300, "fields 必须是列表")

        entity = DataFactoryEntity.objects.get(id=entity_id)
        with transaction.atomic():
            saved_fields = self.save_schema_fields(entity, fields, replace)

        return ResponseData.success(RESPONSE_MSG_0001, saved_fields, len(saved_fields))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview_values(self, request: Request):
        fields = request.data.get('fields') or []
        context = request.data.get('context') or {}
        entity_id = request.data.get('entity_id')
        if not isinstance(fields, list):
            raise ToolsError(300, "fields 必须是列表")

        test_data = None
        if entity_id:
            entity = DataFactoryEntity.objects.select_related('project_product').get(id=entity_id)
            test_data = DataFactoryRuntimeCache.build_test_data(
                entity.project_product_id,
                request.data.get('test_env'),
            )

        payload = {}
        rows = []
        for field_data in fields:
            field_data = dict(field_data)
            try:
                field_data["generator_config"] = field_data.get("generator_config") or {}
                self.normalize_field_data(field_data)
                field = DataFactoryField(
                    name=field_data.get("name"),
                    label=field_data.get("label") or field_data.get("name"),
                    db_type=field_data.get("db_type") or field_data.get("platform_type") or "string",
                    platform_type=field_data.get("platform_type") or "string",
                    nullable=field_data.get("nullable", True),
                    primary_key=field_data.get("primary_key", False),
                    autoincrement=field_data.get("autoincrement", False),
                    max_length=field_data.get("max_length"),
                    enum_values=field_data.get("enum_values") or [],
                    generator_type=field_data.get("generator_type", DataFactoryGeneratorTypeEnum.FIXED.value),
                    generator_config=field_data.get("generator_config") or {},
                    sort=field_data.get("sort", 0),
                )
                if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                    rows.append({
                        "name": field.name,
                        "value": field.generator_config.get("reason") or "数据库生成",
                        "valid": True,
                        "message": "跳过字段",
                    })
                    continue
                if field.generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
                    dependency_preview = self.preview_dependency_field(field, context)
                    if dependency_preview is not None:
                        rows.append(dependency_preview)
                        continue

                value = DataFactoryValueGenerator.generate(field, payload, context)
                value = DataFactoryValueGenerator.replace_value(value, test_data)
                value = DataFactoryTypeCast.cast(value, field.platform_type)
                DataFactoryValueGenerator.validate(field, value)
                payload[field.name] = value
                rows.append({
                    "name": field.name,
                    "value": DataFactoryTypeCast.to_jsonable(value),
                    "valid": True,
                    "message": "",
                })
            except Exception as error:
                rows.append({
                    "name": field_data.get("name"),
                    "value": None,
                    "valid": False,
                    "message": str(error),
                })

        return ResponseData.success(RESPONSE_MSG_0001, {
            "payload": DataFactoryTypeCast.to_jsonable(payload),
            "fields": rows,
        }, len(rows))

    @staticmethod
    def normalize_field_data(field_data: dict):
        generator_type = field_data.get("generator_type")
        generator_config = field_data.get("generator_config") or {}
        enum_values = field_data.get("enum_values") or []
        if generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = generator_config.get("values") or enum_values
            if not values:
                field_data["generator_type"] = DataFactoryGeneratorTypeEnum.FIXED.value
                field_data["generator_config"] = {"value": ""}
        if generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = generator_config.get("value")
            field_data["generator_config"] = {"value": value or ""}
        if generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            field_data["generator_config"] = validate_data_factory_generator_config(
                DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                DataFactoryFieldViews.normalize_dependency_config(generator_config),
                allow_dependency_template=False,
            )

    @staticmethod
    def normalize_dependency_config(generator_config: dict) -> dict:
        config = dict(generator_config or {})
        normalized = {
            "dependency_entity_id": config.get("dependency_entity_id"),
            "field": config.get("field") or "id",
        }
        return {key: value for key, value in normalized.items() if value not in [None, ""]}

    @staticmethod
    def preview_dependency_field(field: DataFactoryField, context: dict):
        config = field.generator_config or {}
        alias = config.get("alias")
        target_field = config.get("field", "id")
        if alias and alias in context:
            return None

        if alias:
            value = f"${{{{{alias}.{target_field}}}}}"
            message = "依赖字段，当前复用上下文占位值"
            valid = True
        elif config.get("dependency_entity_id"):
            value = f"${{{{依赖实体:{config.get('dependency_entity_id')}.{target_field}}}}}"
            message = "依赖实体字段，状态模板/API中需选择依赖状态模板"
            valid = True
        else:
            value = None
            message = "依赖字段未配置依赖实体"
            valid = False

        return {
            "name": field.name,
            "value": value,
            "valid": valid,
            "message": message,
        }
