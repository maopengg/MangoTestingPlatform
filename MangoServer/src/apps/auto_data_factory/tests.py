# -*- coding: utf-8 -*-

from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_data_factory.models import DataFactoryField
from src.apps.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.apps.auto_data_factory.service.discover import DataFactoryDiscover
from src.apps.auto_data_factory.service.generator import DataFactoryValueGenerator
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.apps.auto_data_factory.service.type_cast import DataFactoryTypeCast
from src.apps.auto_data_factory.views.field import DataFactoryFieldSerializer
from src.apps.auto_data_factory.views.template import DataFactoryTemplateSerializer
from src.common.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.common.exceptions import DataFactoryError
from src.common.models.data_factory_model import DataFactoryFieldOverrideRules, validate_data_factory_scene_overrides


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


class DataFactoryCleanupTests(SimpleTestCase):
    def test_compile_insert_sql_records_sql_and_params(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "contract_category",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        statement = insert(table).values(name="合同类型")

        insert_sql, insert_sql_params = DataFactoryRunner.compile_insert_sql(statement, engine.dialect)

        self.assertIn("INSERT INTO contract_category", insert_sql)
        self.assertEqual(insert_sql_params, {"name": "合同类型"})
        engine.dispose()

    def test_compile_cleanup_sql_records_sql_and_params(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, delete

        engine = create_engine("sqlite://")
        table = Table(
            "contract_category",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        statement = delete(table).where(table.c.id == 12)

        cleanup_sql, cleanup_sql_params = DataFactoryCleanup.compile_cleanup_sql(statement, engine.dialect)

        self.assertIn("DELETE FROM contract_category", cleanup_sql)
        self.assertEqual(cleanup_sql_params, {"id_1": 12})
        engine.dispose()

    def test_delete_without_matching_row_is_not_successful(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        with self.assertRaises(Exception) as error:
            DataFactoryCleanup.validate_delete_result(item, result, "contract_category", "_id", 12)

        self.assertIn("未命中任何记录", str(error.exception))

    def test_force_cleanup_allows_already_missing_row(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        DataFactoryCleanup.validate_delete_result(
            item,
            result,
            "contract_category",
            "_id",
            12,
            allow_missing=True,
        )

    def test_auto_cleanup_allows_already_missing_row(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        DataFactoryCleanup.validate_delete_result(
            item,
            result,
            "contract_category",
            "_id",
            12,
            allow_missing=True,
        )

    def test_cleanup_across_databases_is_rejected(self):
        items = [
            SimpleNamespace(database_id=1),
            SimpleNamespace(database_id=2),
        ]

        with self.assertRaises(Exception) as error:
            DataFactoryCleanup.cleanup_items_in_database_transaction(items)

        self.assertIn("跨库事务一致性", str(error.exception))


class DataFactoryPreviewTests(SimpleTestCase):
    def test_build_dependency_tree_includes_fields_and_status(self):
        node = DataFactoryRunner.build_dependency_tree(
            template=None,
            entity=None,
            alias="合同类型角色",
            action="create",
            fields=[{"name": "role_id", "valid": False}],
            missing_fields=[{"field": "role_id", "message": "必填字段生成结果为空"}],
        )

        self.assertEqual(node["status"], "warning")
        self.assertEqual(node["missing_count"], 1)
        self.assertEqual(node["fields"][0]["name"], "role_id")

    def test_collect_preview_missing_fields_includes_dependencies(self):
        result = DataFactoryRunner.collect_preview_missing_fields(
            template={"id": 1, "name": "合同类型"},
            entity={"id": 10, "name": "contract_category", "table_name": "contract_category"},
            missing_fields=[],
            dependencies=[
                {
                    "template": {"id": 2, "name": "合同类型角色"},
                    "entity": {
                        "id": 11,
                        "name": "contract_category_role",
                        "table_name": "contract_category_role",
                    },
                    "missing_fields": [{"field": "role_id", "message": "必填字段生成结果为空"}],
                    "dependencies": [],
                }
            ],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["field"], "role_id")
        self.assertEqual(result[0]["path"], "合同类型 / 合同类型角色")


class DataFactoryTemplateSerializerTests(SimpleTestCase):
    def test_entity_module_mismatch_raises_data_factory_error(self):
        serializer = DataFactoryTemplateSerializer()
        attrs = {
            "project_product": SimpleNamespace(id=3),
            "module": SimpleNamespace(id=217, project_product_id=3),
            "entity": SimpleNamespace(id=18, project_product_id=3, module_id=213),
            "name": "文件信息表场景",
        }

        with self.assertRaises(DataFactoryError) as error:
            serializer.validate(attrs)

        self.assertEqual(error.exception.msg, "实体不属于当前模块")


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

    def test_scene_override_accepts_main_and_items(self):
        result = validate_data_factory_scene_overrides({
            "__main__": {
                "name": {
                    "generator_type": DataFactoryGeneratorTypeEnum.FIXED.value,
                    "generator_config": {"value": "主表"},
                },
            },
            "__items__": {
                "20": {
                    "category_id": {
                        "generator_type": DataFactoryGeneratorTypeEnum.FIXED.value,
                        "generator_config": {"value": 1},
                    },
                },
            },
        })

        self.assertEqual(result["__main__"]["name"]["generator_config"]["value"], "主表")
        self.assertEqual(result["__items__"]["20"]["category_id"]["generator_config"]["value"], 1)

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

    def test_extract_comment_enum_options_with_parentheses_and_equals(self):
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("状态（0=无效，1=有效）", "integer"),
            [
                {"label": "无效", "value": 0},
                {"label": "有效", "value": 1},
            ],
        )
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("状态 0（无效） 1（有效）", "integer"),
            [
                {"label": "无效", "value": 0},
                {"label": "有效", "value": 1},
            ],
        )

    def test_db_enum_options_use_comment_labels(self):
        self.assertEqual(
            DataFactoryDiscover.extract_enum_options("ENUM('0','1')", "状态：0无效，1有效", "enum"),
            [
                {"label": "无效", "value": "0"},
                {"label": "有效", "value": "1"},
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
