# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现服务

from __future__ import annotations

import re
from typing import Any

from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_DISCOVER_REQUIRED,
    DATA_FACTORY_DISCOVER_READ_FAILED,
    DATA_FACTORY_DISCOVER_NOT_FOUND,
    DATA_FACTORY_DISCOVER_READ_FAILED_CODE_READ_FAILED,
    DATA_FACTORY_DISCOVER_SQL_READ_FAILED,
    DataFactoryError,
)
from src.apps.data_factory.models import Database
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from .datasource import DataFactoryDatasource


class DataFactoryDiscover:
    """通过 SQLAlchemy inspector 发现外部业务库结构。"""

    @classmethod
    def get_tables(cls, database: Database, *, timeout_seconds: int | None = None) -> list[dict[str, Any]]:
        engine = DataFactoryDatasource.create_engine(database, timeout_seconds=timeout_seconds)
        try:
            from sqlalchemy import inspect, text

            if engine.dialect.name in {"mysql", "postgresql"}:
                if engine.dialect.name == "mysql":
                    sql = text(
                        "SELECT TABLE_NAME AS name, TABLE_COMMENT AS comment FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = :database_name AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
                    )
                    parameters = {"database_name": database.database_name}
                else:
                    sql = text(
                        "SELECT n.nspname AS schema_name, c.relname AS name, COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment "
                        "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = COALESCE(NULLIF(:schema_name, ''), current_schema()) AND c.relkind IN ('r', 'p') "
                        "AND has_table_privilege(c.oid, 'SELECT') ORDER BY c.relname"
                    )
                    parameters = {'schema_name': database.schema_name}
                with engine.connect() as connection:
                    return [{"name": row["name"], "schema_name": row.get("schema_name", database.schema_name),
                             "comment": row["comment"] or ""}
                            for row in connection.execute(sql, parameters).mappings()]

            inspector = inspect(engine)
            tables = []
            for table_name in sorted(inspector.get_table_names()):
                tables.append({
                    "name": table_name,
                    "comment": cls._get_table_comment(inspector, table_name),
                })
            return tables
        except Exception as error:
            from sqlalchemy.exc import SQLAlchemyError
            if isinstance(error, SQLAlchemyError):
                from src.apps.data_factory.services.data_source_error import DataSourceErrorService
                DataSourceErrorService.raise_sql_error(database, error)
            raise DataFactoryError(DATA_FACTORY_DISCOVER_READ_FAILED,
                                   value=(DataFactoryDatasource._safe_error(database, error),)) from error
        finally:
            engine.dispose()

    @classmethod
    def get_table_schema(cls, database: Database, table_name: str, *, timeout_seconds: int | None = None) -> dict[
        str, Any]:
        if not table_name:
            raise DataFactoryError(DATA_FACTORY_DISCOVER_REQUIRED)

        engine = DataFactoryDatasource.create_engine(database, timeout_seconds=timeout_seconds)
        try:
            from sqlalchemy import inspect

            inspector = inspect(engine)
            schema_name = database.schema_name or (
                inspector.default_schema_name if database.db_type == DataSourceTypeEnum.POSTGRESQL.value else None)
            if table_name not in inspector.get_table_names(schema=schema_name):
                raise DataFactoryError(DATA_FACTORY_DISCOVER_NOT_FOUND, value=(table_name,))

            pk = inspector.get_pk_constraint(table_name, schema=schema_name) or {}
            pk_columns = pk.get("constrained_columns") or []
            indexes = inspector.get_indexes(table_name, schema=schema_name)
            foreign_keys = inspector.get_foreign_keys(table_name, schema=schema_name)
            unique_columns = cls._get_unique_columns(indexes)

            auto_generated_columns = cls._get_mysql_auto_generated_columns(
                engine,
                table_name,
            )
            columns = []
            for index, column in enumerate(inspector.get_columns(table_name, schema=schema_name)):
                columns.append(cls._normalize_column(
                    column,
                    pk_columns,
                    unique_columns,
                    index,
                    auto_generated_columns=auto_generated_columns,
                ))

            return {
                "table": table_name,
                "schema_name": schema_name or '',
                "table_comment": cls._get_table_comment(inspector, table_name, schema_name),
                "primary_keys": pk_columns,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
            }
        except DataFactoryError:
            raise
        except Exception as error:
            from sqlalchemy.exc import SQLAlchemyError
            if isinstance(error, SQLAlchemyError):
                from src.apps.data_factory.services.data_source_error import DataSourceErrorService
                DataSourceErrorService.raise_sql_error(database, error)
            raise DataFactoryError(DATA_FACTORY_DISCOVER_READ_FAILED_CODE_READ_FAILED,
                                   value=(DataFactoryDatasource._safe_error(database, error),)) from error
        finally:
            engine.dispose()

    @classmethod
    def get_mysql_table_schemas(
            cls,
            database: Database,
            table_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """批量读取字段；对元数据未声明生成方式的主键，补读真实 DDL。"""
        if not table_names:
            return {}
        engine = DataFactoryDatasource.create_engine(database)
        try:
            from sqlalchemy import bindparam, text

            statement = text("""
                             SELECT TABLE_NAME,
                                    COLUMN_NAME,
                                    COLUMN_TYPE,
                                    IS_NULLABLE,
                                    COLUMN_KEY,
                                    EXTRA,
                                    COLUMN_DEFAULT,
                                    CHARACTER_MAXIMUM_LENGTH,
                                    ORDINAL_POSITION
                             FROM information_schema.COLUMNS
                             WHERE TABLE_SCHEMA = :schema_name
                               AND TABLE_NAME IN :table_names
                             ORDER BY TABLE_NAME, ORDINAL_POSITION
                             """).bindparams(bindparam("table_names", expanding=True))
            with engine.connect() as connection:
                rows = connection.execute(
                    statement,
                    {"schema_name": database.database_name, "table_names": sorted(set(table_names))},
                ).mappings()
                result: dict[str, dict[str, Any]] = {}
                for row in rows:
                    table_name = row["TABLE_NAME"]
                    db_type = str(row["COLUMN_TYPE"] or "").upper()
                    platform_type = cls.normalize_type(db_type)
                    result.setdefault(table_name, {"table": table_name, "columns": []})["columns"].append({
                        "name": row["COLUMN_NAME"],
                        "db_type": db_type,
                        "platform_type": platform_type,
                        "nullable": row["IS_NULLABLE"] == "YES",
                        "primary_key": row["COLUMN_KEY"] == "PRI",
                        "autoincrement": any(
                            marker in str(row["EXTRA"] or "").lower()
                            for marker in ("auto_increment", "auto_random")
                        ),
                        "default": row["COLUMN_DEFAULT"],
                        "generated": "generated" in str(row["EXTRA"] or "").lower(),
                        "max_length": row["CHARACTER_MAXIMUM_LENGTH"],
                        "enum_values": cls.extract_enum_values(db_type),
                    })
                for table_name, schema in result.items():
                    candidates = [
                        column for column in schema["columns"]
                        if column["primary_key"] and not column["autoincrement"]
                    ]
                    if not candidates:
                        continue
                    # TiDB 的 COLUMNS.EXTRA 可能不包含 AUTO_RANDOM；不能据此认定生成属性被移除。
                    generated_kinds = cls.get_mysql_generated_column_kinds(
                        connection, table_name, schema_name=database.database_name,
                    )
                    for column in candidates:
                        column["autoincrement"] = column["name"] in generated_kinds
                return result
        except Exception as error:
            raise DataFactoryError(DATA_FACTORY_DISCOVER_SQL_READ_FAILED,
                                   value=(DataFactoryDatasource._safe_error(database, error),)) from error
        finally:
            engine.dispose()

    @staticmethod
    def _get_table_comment(inspector, table_name: str, schema_name=None) -> str:
        try:
            table_comment = inspector.get_table_comment(table_name, schema=schema_name) or {}
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
            auto_generated_columns: set[str] | None = None,
    ) -> dict[str, Any]:
        name = column["name"]
        label = column.get("comment") or name
        db_type = str(column["type"])
        platform_type = cls.normalize_type(db_type)
        enum_options = cls.extract_enum_options(db_type, label, platform_type)
        enum_values = [item["value"] for item in enum_options]
        autoincrement = (
                bool(column.get("autoincrement"))
                or name in (auto_generated_columns or set())
        )
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
    def _get_mysql_auto_generated_columns(engine, table_name: str) -> set[str]:
        """补齐 SQLAlchemy 反射无法识别的 TiDB AUTO_RANDOM 字段。"""
        if engine.dialect.name != "mysql":
            return set()
        try:
            with engine.connect() as connection:
                return set(DataFactoryDiscover.get_mysql_generated_column_kinds(connection, table_name))
        except Exception:
            return set()

    @staticmethod
    def get_mysql_generated_column_kinds(connection, table_name: str, schema_name: str | None = None) -> dict[str, str]:
        """Read SQL generation attributes without conflating AUTO_RANDOM with AUTO_INCREMENT."""
        if connection.dialect.name != "mysql":
            return {}
        from sqlalchemy import text

        quote = connection.dialect.identifier_preparer.quote
        quoted_table = quote(table_name)
        if schema_name:
            quoted_table = f"{quote(schema_name)}.{quoted_table}"
        row = connection.execute(text(f"SHOW CREATE TABLE {quoted_table}")).first()
        create_sql = str(row[1] or "") if row and len(row) > 1 else ""
        if not create_sql.strip() or not re.match(r"\s*CREATE\s+TABLE\b", create_sql, re.IGNORECASE):
            raise DataFactoryError(DATA_FACTORY_DISCOVER_SQL_READ_FAILED,
                                   value=("未返回有效的表结构 DDL，无法确认主键生成属性",))
        generated_columns = {}
        for line in create_sql.splitlines():
            match = re.match(r"\s*`((?:[^`]|``)+)`\s+(.*)", line)
            if not match:
                continue
            definition = re.sub(r"'(?:[^'\\]|\\.|'')*'", "", match.group(2))
            kind = re.search(r"\bAUTO_(?:INCREMENT|RANDOM)\b", definition, re.IGNORECASE)
            if kind:
                generated_columns[match.group(1).replace("``", "`")] = kind.group(0).lower()
        return generated_columns

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
            db_options = [{"label": str(value), "value": cls.cast_enum_value(value, platform_type)} for value in
                          db_enum_values]
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
