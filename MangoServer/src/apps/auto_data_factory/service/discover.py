# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现服务

from __future__ import annotations

import re
from typing import Any

from src.apps.auto_system.models import Database
from src.common.enums.data_factory_enum import DataFactoryGeneratorTypeEnum
from src.common.exceptions import ToolsError

from .datasource import DataFactoryDatasource


class DataFactoryDiscover:
    """通过 SQLAlchemy inspector 发现外部业务库结构。"""

    @classmethod
    def get_tables(cls, database: Database) -> list[dict[str, Any]]:
        engine = DataFactoryDatasource.create_engine(database)
        try:
            from sqlalchemy import inspect

            inspector = inspect(engine)
            tables = []
            for table_name in sorted(inspector.get_table_names()):
                tables.append({
                    "name": table_name,
                    "comment": cls._get_table_comment(inspector, table_name),
                })
            return tables
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
                "table_comment": cls._get_table_comment(inspector, table_name),
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

    @staticmethod
    def _get_table_comment(inspector, table_name: str) -> str:
        try:
            table_comment = inspector.get_table_comment(table_name) or {}
            return table_comment.get("text") or ""
        except Exception:
            return ""

    @classmethod
    def _normalize_column(
            cls,
            column: dict[str, Any],
            pk_columns: list[str],
            unique_columns: set[str],
            sort: int,
    ) -> dict[str, Any]:
        name = column["name"]
        label = column.get("comment") or name
        db_type = str(column["type"])
        platform_type = cls.normalize_type(db_type)
        enum_options = cls.extract_enum_options(db_type, label, platform_type)
        enum_values = [item["value"] for item in enum_options]
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
            enum_options=enum_options,
            primary_key=primary_key,
            autoincrement=autoincrement,
        )

        return {
            "name": name,
            "label": label,
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
    def extract_enum_options(cls, db_type: str, label: str, platform_type: str) -> list[dict[str, Any]]:
        db_enum_values = cls.extract_enum_values(db_type)
        comment_options = cls.extract_comment_enum_options(label, platform_type)
        if db_enum_values:
            db_options = [{"label": str(value), "value": cls.cast_enum_value(value, platform_type)} for value in db_enum_values]
            comment_option_map = {item["value"]: item["label"] for item in comment_options}
            if comment_option_map:
                return [
                    {
                        "label": comment_option_map.get(item["value"], item["label"]),
                        "value": item["value"],
                    }
                    for item in db_options
                ]
            return db_options
        return comment_options

    @classmethod
    def extract_comment_enum_options(cls, label: str, platform_type: str) -> list[dict[str, Any]]:
        """Extract options from comments like "是否有效，1 有效，0 无效"."""
        if not label:
            return []

        text = re.sub(r"\s+", " ", str(label)).strip()
        pattern = re.compile(
            r"(?<![\d.])(?P<value>-?\d+(?:\.\d+)?)\s*[：:=、，,.;；。/-]?"
            r"(?=\s*[（(【\[]?\s*[\u4e00-\u9fa5A-Za-z])"
        )
        matches = list(pattern.finditer(text))
        options = []
        for index, match in enumerate(matches):
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            option_label = text[match.end():next_start].strip(" ：:=、，,；;。.（）()【】[]-")
            if not option_label or re.fullmatch(r"-?\d+(?:\.\d+)?", option_label):
                continue
            value = cls.cast_enum_value(match.group("value"), platform_type)
            if any(item["value"] == value for item in options):
                continue
            options.append({"label": option_label, "value": value})

        return options if len(options) >= 2 else []

    @staticmethod
    def cast_enum_value(value: Any, platform_type: str) -> Any:
        if platform_type == "integer":
            return int(float(value))
        if platform_type == "decimal":
            return float(value)
        if platform_type == "boolean":
            return str(value).lower() in ["true", "1", "yes", "y"]
        return str(value)

    @classmethod
    def recommend_generator_type(
            cls,
            name: str,
            platform_type: str,
            primary_key: bool,
            autoincrement: bool,
            enum_values: list[Any],
    ) -> int:
        if primary_key and autoincrement:
            return DataFactoryGeneratorTypeEnum.SKIP.value
        if cls.recommend_test_data_method(name):
            if name in ["password", "passwd", "pwd"]:
                return DataFactoryGeneratorTypeEnum.FIXED.value
            return DataFactoryGeneratorTypeEnum.FUNCTION.value
        if name.endswith("_id"):
            return DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value
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
            enum_values: list[Any],
            enum_options: list[dict[str, Any]] | None = None,
            primary_key: bool = False,
            autoincrement: bool = False,
    ) -> dict[str, Any]:
        if primary_key and autoincrement:
            return {"reason": "数据库自增主键"}
        method_value = DataFactoryDiscover.recommend_test_data_method(name)
        if method_value:
            if name in ["password", "passwd", "pwd"]:
                return {"value": "123456"}
            return {"value": method_value}
        if name.endswith("_id"):
            return {}
        if enum_values:
            return {
                "values": enum_values,
                "options": enum_options or [{"label": str(value), "value": value} for value in enum_values],
                "mode": "fixed",
                "value": enum_values[0] if enum_values else None,
            }
        if platform_type == "integer":
            return {}
        if platform_type == "decimal":
            return {}
        return {}

    @staticmethod
    def recommend_test_data_method(name: str) -> str | None:
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
