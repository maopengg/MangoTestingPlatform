# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段值生成

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from src.auto_test.auto_data_factory.models import DataFactoryField
from src.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.exceptions import ToolsError
from src.tools.obtain_test_data import ObtainTestData

from .type_cast import DataFactoryTypeCast


class DataFactoryValueGenerator:
    @classmethod
    def build_payload(
            cls,
            fields: list[DataFactoryField],
            overrides: dict | None = None,
            context: dict | None = None,
    ) -> dict:
        overrides = overrides or {}
        context = context or {}
        payload = {}

        for field in fields:
            if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                continue
            if field.name in overrides:
                value = overrides[field.name]
            else:
                value = cls.generate(field, payload, context)

            value = cls.replace_value(value)
            value = DataFactoryTypeCast.cast(value, field.platform_type)
            cls.validate(field, value)
            payload[field.name] = value

        return payload

    @classmethod
    def generate(cls, field: DataFactoryField, payload: dict, context: dict):
        config = field.generator_config or {}
        generator_type = field.generator_type

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
        if generator_type == DataFactoryGeneratorTypeEnum.AUTO_CODE.value:
            prefix = config.get("prefix", f"AUTO_{field.name.upper()}_")
            length = int(config.get("length", 8))
            return f"{prefix}{uuid.uuid4().hex[:length].upper()}"
        if generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = config.get("values") or field.enum_values
            if not values:
                raise ToolsError(300, f"字段 {field.name} 未配置枚举值")
            if config.get("mode") == "random":
                return random.choice(values)
            return config.get("value", values[0])
        if generator_type == DataFactoryGeneratorTypeEnum.EXPRESSION.value:
            return cls.eval_expression(str(config.get("expression", "")), payload, context)
        if generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            alias = config.get("alias")
            target_field = config.get("field", "id")
            if alias not in context:
                raise ToolsError(300, f"字段 {field.name} 依赖的实体上下文不存在：{alias}")
            return context[alias].get(target_field)
        if generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = config.get("value") or config.get("expression") or config.get("template")
            if not value:
                raise ToolsError(300, f"字段 {field.name} 未配置测试数据方法表达式")
            return value
        if generator_type == DataFactoryGeneratorTypeEnum.SQL_QUERY.value:
            raise ToolsError(300, f"字段 {field.name} 的生成方式暂未实现")

        return None

    @classmethod
    def replace_value(cls, value):
        if isinstance(value, str):
            return ObtainTestData().replace(value)
        if isinstance(value, list):
            return [cls.replace_value(item) for item in value]
        if isinstance(value, dict):
            return {key: cls.replace_value(item) for key, item in value.items()}
        return value

    @staticmethod
    def eval_expression(expression: str, payload: dict, context: dict):
        if not expression:
            return None
        safe_globals = {"__builtins__": {}}
        safe_locals = {"payload": payload, "context": context, **payload}
        try:
            return eval(expression, safe_globals, safe_locals)
        except Exception as error:
            raise ToolsError(300, f"表达式执行失败：{expression}") from error

    @staticmethod
    def validate(field: DataFactoryField, value):
        if value is None and not field.nullable and not field.primary_key:
            raise ToolsError(300, f"字段 {field.name} 必填，但生成结果为空")
        if field.max_length and isinstance(value, str) and len(value) > field.max_length:
            raise ToolsError(300, f"字段 {field.name} 超过最大长度 {field.max_length}")
        if field.enum_values and value not in field.enum_values:
            raise ToolsError(300, f"字段 {field.name} 只能是 {field.enum_values}，当前是 {value}")
