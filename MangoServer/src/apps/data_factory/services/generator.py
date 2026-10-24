import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_GENERATOR_FIELD_GENERATE_UNSUPPORTED,
    DATA_FACTORY_GENERATOR_FIELD_RESULT_GENERATE_INVALID,
    DATA_FACTORY_GENERATOR_FIELD_TOO_LONG,
    DATA_FACTORY_GENERATOR_FIELD_INVALID,
    DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED,
    DATA_FACTORY_GENERATOR_ENTITY_FIELD_NOT_FOUND,
    DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED_CODE_FIELD_CONFIG_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryField
from src.common.testing import ObtainTestData
from .type_cast import DataFactoryTypeCast


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段值生成


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
            raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_GENERATE_UNSUPPORTED, value=(field.name,))

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
                raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED, value=(field.name,))
            if config.get("mode") == "random":
                return random.choice(values)
            return config.get("value", values[0])
        if generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            alias = config.get("alias")
            target_field = config.get("field", "id")
            if alias not in context:
                raise DataFactoryError(DATA_FACTORY_GENERATOR_ENTITY_FIELD_NOT_FOUND, value=(field.name, alias))
            return context[alias].get(target_field)
        if generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = config.get("value")
            if not value:
                raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_CONFIG_REQUIRED_CODE_FIELD_CONFIG_REQUIRED,
                                       value=(field.name,))
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
            raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_RESULT_GENERATE_INVALID, value=(field.name,))
        if field.max_length and isinstance(value, str) and len(value) > field.max_length:
            raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_TOO_LONG, value=(field.name, field.max_length))
        if field.enum_values and value not in field.enum_values:
            raise DataFactoryError(DATA_FACTORY_GENERATOR_FIELD_INVALID, value=(field.name, field.enum_values, value))
