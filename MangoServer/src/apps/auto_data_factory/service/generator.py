# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段值生成

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from src.apps.auto_data_factory.models import DataFactoryField
from src.common.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.common.exceptions import ToolsError
from src.common.tools.obtain_test_data import ObtainTestData

from .type_cast import DataFactoryTypeCast


class DataFactoryValueGenerator:
    @classmethod
    def build_payload(
            cls,
            fields: list[DataFactoryField],
            overrides: dict | None = None,
            context: dict | None = None,
            test_data: ObtainTestData | None = None,
    ) -> dict:
        overrides = overrides or {}
        context = context or {}
        test_data = test_data or ObtainTestData()
        payload = {}

        for field in fields:
            if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                continue
            if field.name in overrides:
                value = overrides[field.name]
            else:
                value = cls.generate(field, payload, context)

            value = cls.replace_value(value, test_data)
            value = DataFactoryTypeCast.cast(value, field.platform_type)
            cls.validate(field, value)
            payload[field.name] = value

        return payload

    @classmethod
    def generate(cls, field: DataFactoryField, payload: dict, context: dict):
        config = field.generator_config or {}
        generator_type = field.generator_type
        supported_generator_types = {
            DataFactoryGeneratorTypeEnum.FIXED.value,
            DataFactoryGeneratorTypeEnum.RANDOM_STRING.value,
            DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value,
            DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value,
            DataFactoryGeneratorTypeEnum.NOW.value,
            DataFactoryGeneratorTypeEnum.RELATIVE_TIME.value,
            DataFactoryGeneratorTypeEnum.UUID.value,
            DataFactoryGeneratorTypeEnum.ENUM.value,
            DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            DataFactoryGeneratorTypeEnum.FUNCTION.value,
        }
        if generator_type not in supported_generator_types:
            raise ToolsError(300, f"字段 {field.name} 的生成方式不支持")

        if generator_type not in [
            DataFactoryGeneratorTypeEnum.ENUM.value,
            DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
        ] and config.get("value") not in [None, ""]:
            return config.get("value")
        if generator_type == DataFactoryGeneratorTypeEnum.FIXED.value:
            return config.get("value")
        if generator_type == DataFactoryGeneratorTypeEnum.RANDOM_STRING.value:
            prefix = config.get("prefix", "")
            length = int(config.get("length", 8))
            return f"{prefix}{uuid.uuid4().hex[:length]}"
        if generator_type == DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value:
            return random.randint(int(config.get("min", 1)), int(config.get("max", 100)))
        if generator_type == DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value:
            min_value = Decimal(str(config.get("min", 1)))
            max_value = Decimal(str(config.get("max", 100)))
            precision = int(config.get("precision", 2))
            value = min_value + (max_value - min_value) * Decimal(str(random.random()))
            return value.quantize(Decimal("1." + "0" * precision))
        if generator_type == DataFactoryGeneratorTypeEnum.NOW.value:
            return datetime.now()
        if generator_type == DataFactoryGeneratorTypeEnum.RELATIVE_TIME.value:
            return datetime.now() + timedelta(
                days=int(config.get("days", 0)),
                hours=int(config.get("hours", 0)),
                minutes=int(config.get("minutes", 0)),
            )
        if generator_type == DataFactoryGeneratorTypeEnum.UUID.value:
            return str(uuid.uuid4()) if config.get("dash", False) else uuid.uuid4().hex
        if generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = config.get("values") or field.enum_values
            if not values:
                raise ToolsError(300, f"字段 {field.name} 未配置枚举值")
            if config.get("mode") == "random":
                return random.choice(values)
            return config.get("value", values[0])
        if generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            alias = config.get("alias")
            target_field = config.get("field", "id")
            if alias not in context:
                raise ToolsError(300, f"字段 {field.name} 依赖的实体上下文不存在：{alias}")
            return context[alias].get(target_field)
        if generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = config.get("value")
            if not value:
                raise ToolsError(300, f"字段 {field.name} 未配置测试数据方法")
            return value

        return None

    @classmethod
    def replace_value(cls, value, test_data: ObtainTestData | None = None):
        test_data = test_data or ObtainTestData()
        if isinstance(value, str):
            return test_data.replace(value)
        if isinstance(value, list):
            return [cls.replace_value(item, test_data) for item in value]
        if isinstance(value, dict):
            return {key: cls.replace_value(item, test_data) for key, item in value.items()}
        return value

    @staticmethod
    def validate(field: DataFactoryField, value):
        if value is None and not field.nullable and not field.primary_key:
            raise ToolsError(300, f"字段 {field.name} 必填，但生成结果为空")
        if field.max_length and isinstance(value, str) and len(value) > field.max_length:
            raise ToolsError(300, f"字段 {field.name} 超过最大长度 {field.max_length}")
        if field.enum_values and value not in field.enum_values:
            raise ToolsError(300, f"字段 {field.name} 只能是 {field.enum_values}，当前是 {value}")
