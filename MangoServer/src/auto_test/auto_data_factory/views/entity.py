# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂实体视图

from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_data_factory.models import DataFactoryEntity, DataFactoryField
from src.auto_test.auto_data_factory.service.generator import DataFactoryValueGenerator
from src.auto_test.auto_data_factory.service.type_cast import DataFactoryTypeCast
from src.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.exceptions import ToolsError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryFieldSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryField
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('entity')

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
            if generator_type == DataFactoryGeneratorTypeEnum.RANDOM_STRING.value:
                if int(generator_config.get("length", 8)) <= 0:
                    raise serializers.ValidationError("随机字符串 length 必须大于 0")

            if generator_type in [
                DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value,
                DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value,
            ]:
                min_value = float(generator_config.get("min", 1))
                max_value = float(generator_config.get("max", 100))
                if min_value > max_value:
                    raise serializers.ValidationError("随机数 min 不能大于 max")
        except (TypeError, ValueError) as error:
            raise serializers.ValidationError("随机生成器的数值配置必须是合法数字") from error

        if generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = generator_config.get("values") or enum_values
            if not values:
                raise serializers.ValidationError("枚举生成器必须配置 values 或字段 enum_values")
            if "value" in generator_config and generator_config["value"] not in values:
                raise serializers.ValidationError("枚举固定值必须在 values 范围内")

        if generator_type == DataFactoryGeneratorTypeEnum.EXPRESSION.value:
            if not generator_config.get("expression"):
                raise serializers.ValidationError("表达式生成器必须配置 expression")

        if generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = generator_config.get("value") or generator_config.get("expression") or generator_config.get("template")
            if not value:
                raise serializers.ValidationError("测试数据方法必须配置 value，例如 ${{character_email()}}")

        if generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            strategy = generator_config.get("strategy", "reuse_or_create")
            if strategy not in ["reuse_or_create", "must_exist", "create_always"]:
                raise serializers.ValidationError("依赖字段 strategy 只能是 reuse_or_create、must_exist、create_always")

        if generator_type == DataFactoryGeneratorTypeEnum.AUTO_CODE.value:
            try:
                if int(generator_config.get("length", 8)) <= 0:
                    raise serializers.ValidationError("自动编号 length 必须大于 0")
            except (TypeError, ValueError) as error:
                raise serializers.ValidationError("自动编号 length 必须是合法数字") from error

        return attrs


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

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'datasource_alias')


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


class DataFactoryFieldCRUD(ModelCRUD):
    model = DataFactoryField
    queryset = DataFactoryField.objects.all()
    serializer_class = DataFactoryFieldSerializer
    serializer = DataFactoryFieldSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['entity']


class DataFactoryFieldViews(ViewSet):
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
        saved_fields = []
        field_names = []
        with transaction.atomic():
            for field_data in fields:
                field_data = {**field_data, "entity": entity.id}
                if not field_data.get("name"):
                    raise ToolsError(300, "字段 name 不能为空")
                self.normalize_field_data(field_data)
                field_names.append(field_data["name"])
                instance = DataFactoryField.objects.filter(entity=entity, name=field_data["name"]).first()
                serializer = DataFactoryFieldSerializer(instance=instance, data=field_data, partial=bool(instance))
                serializer.is_valid(raise_exception=True)
                serializer.save()
                saved_fields.append(serializer.data)

            if replace:
                DataFactoryField.objects.filter(entity=entity).exclude(name__in=field_names).delete()

        return ResponseData.success(RESPONSE_MSG_0001, saved_fields, len(saved_fields))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview_values(self, request: Request):
        fields = request.data.get('fields') or []
        context = request.data.get('context') or {}
        if not isinstance(fields, list):
            raise ToolsError(300, "fields 必须是列表")

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
                value = DataFactoryValueGenerator.replace_value(value)
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
            value = generator_config.get("value") or generator_config.get("expression") or generator_config.get("template")
            field_data["generator_config"] = {"value": value or ""}

    @staticmethod
    def preview_dependency_field(field: DataFactoryField, context: dict):
        config = field.generator_config or {}
        alias = config.get("alias")
        target_field = config.get("field", "id")
        if alias and alias in context:
            return None

        if alias:
            value = f"${{{{{alias}.{target_field}}}}}"
        elif config.get("template_id"):
            value = f"${{{{template:{config.get('template_id')}.{target_field}}}}}"
        else:
            value = "${{依赖模板.id}}"

        return {
            "name": field.name,
            "value": value,
            "valid": True,
            "message": "依赖字段，当前仅展示关联占位值",
        }
