from pydantic import ValidationError
from rest_framework import serializers

from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.data_factory.models import DataFactoryCaseConfig, DataFactoryField
from src.apps.data_factory.schemas.configuration import (
    validate_data_factory_generator_config,
    validate_data_factory_scene_overrides,
)


class DataFactoryFieldSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = DataFactoryField
        fields = "__all__"

    def validate(self, attrs):
        generator_type = attrs.get(
            "generator_type",
            self.instance.generator_type if self.instance else None,
        )
        generator_config = attrs.get(
            "generator_config",
            self.instance.generator_config if self.instance else {},
        ) or {}
        enum_values = attrs.get(
            "enum_values",
            self.instance.enum_values if self.instance else [],
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


class DataFactoryCaseConfigSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = "__all__"

    def to_internal_value(self, data):
        data = data.copy()
        if data.get("cleanup_strategy") == "":
            data["cleanup_strategy"] = None
        if data.get("case") is not None and data.get("source_id") is None:
            data["source_id"] = data.get("case")
        return super().to_internal_value(data)

    def validate(self, attrs):
        source_type = attrs.get("source_type", self.instance.source_type if self.instance else None)
        if source_type not in DataFactoryCaseSourceTypeEnum.obj():
            raise serializers.ValidationError("用例来源类型不正确")
        if not attrs.get("source_id", self.instance.source_id if self.instance else None):
            raise serializers.ValidationError("用例ID不能为空")
        template = attrs.get("template", self.instance.template if self.instance else None)
        if template and template.usage_scope == DataFactoryTemplateUsageScopeEnum.INTERNAL.value:
            raise serializers.ValidationError("仅场景内部引用用途的场景模板不能绑定到用例")
        field_overrides = attrs.get("field_overrides", self.instance.field_overrides if self.instance else {})
        try:
            attrs["field_overrides"] = validate_data_factory_scene_overrides(field_overrides or {})
        except (ValidationError, ValueError) as error:
            raise serializers.ValidationError(f"字段覆盖规则格式错误：{error}") from error
        return attrs
