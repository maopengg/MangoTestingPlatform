# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现服务

from __future__ import annotations

import re
from typing import Any

from src.auto_test.auto_system.models import Database
from src.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.exceptions import ToolsError

from .datasource import DataFactoryDatasource


class DataFactoryDiscover:
    """通过 SQLAlchemy inspector 发现外部业务库结构。"""

    @classmethod
    def get_tables(cls, database: Database) -> list[str]:
        engine = DataFactoryDatasource.create_engine(database)
        try:
            from sqlalchemy import inspect

            inspector = inspect(engine)
            return sorted(inspector.get_table_names())
        except Exception as error:
            raise ToolsError(300, f"读取数据表失败：{error}") from error
        finally:
            engine.dispose()

    @classmethod
    def get_table_schema(cls, database: Database, table_name: str) -> dict[str, Any]:
        if not table_name:
            raise ToolsError(300, "表名不能为空")

        engine = DataFactoryDatasource.create_engine(database)
        try:
            from sqlalchemy import inspect

            inspector = inspect(engine)
            if table_name not in inspector.get_table_names():
                raise ToolsError(300, f"数据表不存在：{table_name}")

            pk = inspector.get_pk_constraint(table_name) or {}
            pk_columns = pk.get("constrained_columns") or []
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            unique_columns = cls._get_unique_columns(indexes)

            columns = []
            for index, column in enumerate(inspector.get_columns(table_name)):
                columns.append(cls._normalize_column(column, pk_columns, unique_columns, index))

            return {
                "table": table_name,
                "primary_keys": pk_columns,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
            }
        except ToolsError:
            raise
        except Exception as error:
            raise ToolsError(300, f"读取表结构失败：{error}") from error
        finally:
            engine.dispose()

    @classmethod
    def _normalize_column(
            cls,
            column: dict[str, Any],
            pk_columns: list[str],
            unique_columns: set[str],
            sort: int,
    ) -> dict[str, Any]:
        name = column["name"]
        db_type = str(column["type"])
        platform_type = cls.normalize_type(db_type)
        enum_values = cls.extract_enum_values(db_type)
        autoincrement = bool(column.get("autoincrement"))
        primary_key = name in pk_columns

        generator_type = cls.recommend_generator_type(
            name=name,
            platform_type=platform_type,
            primary_key=primary_key,
            autoincrement=autoincrement,
            enum_values=enum_values,
        )
        generator_config = cls.recommend_generator_config(
            name=name,
            platform_type=platform_type,
            enum_values=enum_values,
            primary_key=primary_key,
            autoincrement=autoincrement,
        )

        return {
            "name": name,
            "label": column.get("comment") or name,
            "db_type": db_type,
            "platform_type": platform_type,
            "nullable": bool(column.get("nullable")),
            "default": column.get("default"),
            "primary_key": primary_key,
            "autoincrement": autoincrement,
            "max_length": getattr(column["type"], "length", None),
            "enum_values": enum_values,
            "unique": name in unique_columns,
            "generator_type": generator_type,
            "generator_config": generator_config,
            "recommend": {
                "generator_type": generator_type,
                "generator_config": generator_config,
            },
            "output_enabled": not (primary_key and autoincrement),
            "output_name": name,
            "sort": sort,
        }

    @staticmethod
    def _get_unique_columns(indexes: list[dict[str, Any]]) -> set[str]:
        unique_columns = set()
        for index in indexes:
            if index.get("unique"):
                for column_name in index.get("column_names") or []:
                    unique_columns.add(column_name)
        return unique_columns

    @staticmethod
    def normalize_type(db_type: str) -> str:
        upper = db_type.upper()
        if any(item in upper for item in ["BIGINT", "INTEGER", "INT", "SMALLINT"]):
            return "integer"
        if any(item in upper for item in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL"]):
            return "decimal"
        if any(item in upper for item in ["DATETIME", "TIMESTAMP"]):
            return "datetime"
        if re.search(r"\bDATE\b", upper):
            return "date"
        if "BOOLEAN" in upper or "BOOL" in upper or "TINYINT(1)" in upper:
            return "boolean"
        if "JSON" in upper:
            return "json"
        if "ENUM" in upper:
            return "enum"
        return "string"

    @staticmethod
    def extract_enum_values(db_type: str) -> list[str]:
        match = re.search(r"ENUM\((.*)\)", db_type, re.IGNORECASE)
        if not match:
            return []
        return [item.strip().strip("'").strip('"') for item in match.group(1).split(",")]

    @classmethod
    def recommend_generator_type(
            cls,
            name: str,
            platform_type: str,
            primary_key: bool,
            autoincrement: bool,
            enum_values: list[str],
    ) -> int:
        if primary_key and autoincrement:
            return DataFactoryGeneratorTypeEnum.SKIP.value
        if cls.recommend_test_data_expression(name):
            if name in ["password", "passwd", "pwd"]:
                return DataFactoryGeneratorTypeEnum.FIXED.value
            return DataFactoryGeneratorTypeEnum.FUNCTION.value
        if name.endswith("_id"):
            return DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value
        if name.endswith("_no") or name.endswith("_code"):
            return DataFactoryGeneratorTypeEnum.AUTO_CODE.value
        if name in ["created_at", "updated_at", "create_time", "update_time"]:
            return DataFactoryGeneratorTypeEnum.NOW.value
        if enum_values:
            return DataFactoryGeneratorTypeEnum.ENUM.value
        if platform_type == "integer":
            return DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value
        if platform_type == "decimal":
            return DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value
        return DataFactoryGeneratorTypeEnum.FIXED.value

    @staticmethod
    def recommend_generator_config(
            name: str,
            platform_type: str,
            enum_values: list[str],
            primary_key: bool = False,
            autoincrement: bool = False,
    ) -> dict[str, Any]:
        if primary_key and autoincrement:
            return {"reason": "数据库自增主键"}
        expression = DataFactoryDiscover.recommend_test_data_expression(name)
        if expression:
            if name in ["password", "passwd", "pwd"]:
                return {"value": "123456"}
            return {"value": expression}
        if name.endswith("_id"):
            return {"template_id": None, "field": "id", "strategy": "reuse_or_create"}
        if name.endswith("_no") or name.endswith("_code"):
            return {}
        if platform_type == "integer":
            return {}
        if platform_type == "decimal":
            return {}
        if enum_values:
            return {"values": enum_values, "mode": "fixed", "value": enum_values[0] if enum_values else None}
        return {}

    @staticmethod
    def recommend_test_data_expression(name: str) -> str | None:
        lower_name = name.lower()
        if lower_name in ["username", "user_name", "account", "login_name"]:
            return "${{str_lowercase(10)}}"
        if "email" in lower_name:
            return "${{character_email()}}"
        if lower_name in ["full_name", "real_name", "name"]:
            return "${{character_male_name()}}"
        if "phone" in lower_name or "mobile" in lower_name:
            return "${{character_phone()}}"
        if "id_card" in lower_name or "id_number" in lower_name:
            return "${{character_id_number()}}"
        if "address" in lower_name:
            return "${{character_address()}}"
        if "company" in lower_name:
            return "${{character_company()}}"
        if lower_name in ["password", "passwd", "pwd"]:
            return "123456"
        return None
