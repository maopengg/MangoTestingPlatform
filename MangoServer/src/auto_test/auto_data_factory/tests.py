# -*- coding: utf-8 -*-

from django.test import SimpleTestCase
from rest_framework import serializers

from src.auto_test.auto_data_factory.models import DataFactoryField
from src.auto_test.auto_data_factory.service.discover import DataFactoryDiscover
from src.auto_test.auto_data_factory.service.generator import DataFactoryValueGenerator
from src.auto_test.auto_data_factory.service.type_cast import DataFactoryTypeCast
from src.auto_test.auto_data_factory.views.field import DataFactoryFieldSerializer
from src.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.models.data_factory_model import DataFactoryFieldOverrideRules


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

    def test_build_payload_with_fixed_values(self):
        fields = [
            self.build_field("price", "decimal", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": "19.90"}),
            self.build_field("quantity", "integer", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": 2}),
        ]

        payload = DataFactoryValueGenerator.build_payload(fields)

        self.assertEqual(str(payload["price"]), "19.90")
        self.assertEqual(payload["quantity"], 2)

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
            "generator_config": {"dependency_entity_id": 12, "field": "id"},
        })
        self.assertEqual(result["generator_config"]["dependency_entity_id"], 12)
        self.assertEqual(result["generator_config"]["field"], "id")

    def test_dependency_field_rejects_template_id_in_entity_rule(self):
        serializer = DataFactoryFieldSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
                "name": "user_id",
                "db_type": "bigint",
                "platform_type": "integer",
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {"dependency_entity_id": 12, "field": "id", "template_id": 99},
            })

    def test_dependency_override_accepts_template_id(self):
        result = DataFactoryFieldOverrideRules.model_validate({
            "user_id": {
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {
                    "dependency_entity_id": 12,
                    "field": "id",
                    "template_id": 99,
                    "strategy": "reuse_or_create",
                },
            }
        }).model_dump()

        self.assertEqual(result["user_id"]["generator_config"]["template_id"], 99)

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


class DataFactoryDiscoverTests(SimpleTestCase):
    def test_extract_comment_enum_options(self):
        options = DataFactoryDiscover.extract_comment_enum_options("是否有效，1 有效，0 无效", "integer")

        self.assertEqual(options, [
            {"label": "有效", "value": 1},
            {"label": "无效", "value": 0},
        ])

    def test_extract_comment_enum_options_with_compact_separators(self):
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("合同类型状态 0.禁用状态 1.启用状态", "integer"),
            [
                {"label": "禁用状态", "value": 0},
                {"label": "启用状态", "value": 1},
            ],
        )
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("是否签约倒签 0.不是 1.是 2.未知", "integer"),
            [
                {"label": "不是", "value": 0},
                {"label": "是", "value": 1},
                {"label": "未知", "value": 2},
            ],
        )

    def test_comment_enum_options_drive_enum_generator_config(self):
        column = {
            "name": "valid",
            "type": "TINYINT",
            "comment": "是否有效，1 有效，0 无效",
            "nullable": False,
            "autoincrement": False,
        }

        result = DataFactoryDiscover._normalize_column(column, [], set(), 0)

        self.assertEqual(result["generator_type"], DataFactoryGeneratorTypeEnum.ENUM.value)
        self.assertEqual(result["enum_values"], [1, 0])
        self.assertEqual(result["generator_config"]["options"], [
            {"label": "有效", "value": 1},
            {"label": "无效", "value": 0},
        ])
