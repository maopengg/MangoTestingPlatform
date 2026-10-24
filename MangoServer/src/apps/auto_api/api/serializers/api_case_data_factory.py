# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例数据工厂配置视图

from pydantic import ValidationError
from rest_framework import serializers

from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.data_factory.formatters import format_template
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.schemas.configuration import validate_data_factory_scene_overrides
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ApiCaseDataFactorySerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = "__all__"

    def to_internal_value(self, data):
        data = data.copy()
        data['source_type'] = DataFactoryCaseSourceTypeEnum.API_CASE.value
        if data.get("cleanup_strategy") == "":
            data["cleanup_strategy"] = None
        if data.get("case") is not None and data.get("source_id") is None:
            data["source_id"] = data.get("case")
        return super().to_internal_value(data)

    def validate(self, attrs):
        source_id = attrs.get("source_id", self.instance.source_id if self.instance else None)
        if not source_id:
            raise serializers.ValidationError("用例ID不能为空")
        template = attrs.get("template", self.instance.template if self.instance else None)
        if template and template.usage_scope == DataFactoryTemplateUsageScopeEnum.INTERNAL.value:
            raise serializers.ValidationError("仅场景内部引用用途的场景模板不能绑定到用例")
        field_overrides = attrs.get(
            "field_overrides",
            self.instance.field_overrides if self.instance else {},
        )
        try:
            attrs["field_overrides"] = validate_data_factory_scene_overrides(field_overrides or {})
        except (ValidationError, ValueError) as error:
            raise serializers.ValidationError(f"字段覆盖规则格式错误：{error}") from error
        return attrs


class ApiCaseDataFactorySerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    template = RelatedObjectField(formatter=format_template, read_only=True)
    case = serializers.IntegerField(source='source_id', read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryCaseConfig
        fields = '__all__'
