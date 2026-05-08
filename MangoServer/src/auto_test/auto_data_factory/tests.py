# -*- coding: utf-8 -*-

from django.test import SimpleTestCase
from rest_framework import serializers

from src.auto_test.auto_data_factory.models import DataFactoryField
from src.auto_test.auto_data_factory.service.generator import DataFactoryValueGenerator
from src.auto_test.auto_data_factory.service.type_cast import DataFactoryTypeCast
from src.auto_test.auto_data_factory.views.entity import DataFactoryFieldSerializer
from src.enums.data_factory_enum import DataFactoryGeneratorTypeEnum


class DataFactoryTypeCastTests(SimpleTestCase):
    def test_cast_basic_types(self):
        self.assertEqual(DataFactoryTypeCast.cast("1", "integer"), 1)
        self.assertEqual(str(DataFactoryTypeCast.cast("12.30", "decimal")), "12.30")
        self.assertEqual(DataFactoryTypeCast.cast("true", "boolean"), True)
        self.assertEqual(DataFactoryTypeCast.cast({"a": 1}, "json"), {"a": 1})


class DataFactoryGeneratorTests(SimpleTestCase):
    def build_field(self, name, platform_type, generator_type, config=None, nullable=False):
        return DataFactoryField(
            name=name,
            label=name,
            db_type=platform_type,
            platform_type=platform_type,
            nullable=nullable,
            generator_type=generator_type,
            generator_config=config or {},
        )

    def test_build_payload_with_fixed_and_expression(self):
        fields = [
            self.build_field("price", "decimal", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": "19.90"}),
            self.build_field("quantity", "integer", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": 2}),
            self.build_field("total", "decimal", DataFactoryGeneratorTypeEnum.EXPRESSION.value, {"expression": "price * quantity"}),
        ]

        payload = DataFactoryValueGenerator.build_payload(fields)

        self.assertEqual(str(payload["price"]), "19.90")
        self.assertEqual(payload["quantity"], 2)
        self.assertEqual(str(payload["total"]), "39.80")

    def test_dependency_field_reads_context(self):
        field = self.build_field(
            "user_id",
            "integer",
            DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            {"alias": "用户", "field": "id"},
        )

        payload = DataFactoryValueGenerator.build_payload([field], context={"用户": {"id": 88}})

        self.assertEqual(payload["user_id"], 88)

    def test_required_field_cannot_be_empty(self):
        field = self.build_field("name", "string", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": None})

        with self.assertRaises(Exception):
            DataFactoryValueGenerator.build_payload([field])


class DataFactoryFieldSerializerTests(SimpleTestCase):
    def test_dependency_field_can_save_without_template_id(self):
        serializer = DataFactoryFieldSerializer()

        result = serializer.validate({
            "name": "user_id",
            "db_type": "bigint",
            "platform_type": "integer",
            "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            "generator_config": {"alias": "用户", "field": "id"},
        })
        self.assertEqual(result["generator_config"]["field"], "id")

    def test_random_range_must_be_valid(self):
        serializer = DataFactoryFieldSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
            "name": "amount",
            "db_type": "decimal",
            "platform_type": "decimal",
            "generator_type": DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value,
            "generator_config": {"min": 20, "max": 10},
        })
