# -*- coding: utf-8 -*-
from typing import Any

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum


class ApiCaseValidationService:
    """API Case 配置的通用校验。"""

    @classmethod
    def is_empty_value(cls, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set)):
            return all(cls.is_empty_value(item) for item in value)
        if isinstance(value, dict):
            return all(cls.is_empty_value(item) for item in value.values())
        return False

    @classmethod
    def clean_list_rows(cls, value: Any) -> list:
        if not isinstance(value, list):
            return []
        return [item for item in value if not cls.is_empty_value(item)]

    @staticmethod
    def validate_scenario_tags(tags: list[str] | None) -> str | None:
        if tags is None:
            return None
        if not isinstance(tags, list):
            return "scenario_tags 必须是字符串数组。"
        allowed = set(ApiCaseScenarioTagEnum.get_key_list())
        invalid = [tag for tag in tags if not isinstance(tag, str) or tag not in allowed]
        if invalid:
            return f"scenario_tags 包含不支持的标签：{invalid}。"
        return None

    @classmethod
    def validate_sql_rows_datasource_alias(cls, rows: Any, field_name: str) -> str | None:
        if not rows:
            return None
        if not isinstance(rows, list):
            return f"{field_name} 必须是数组。"
        for index, row in enumerate(rows, start=1):
            if cls.is_empty_value(row):
                continue
            if not isinstance(row, dict):
                return f"{field_name}[{index}] 必须是对象，格式为 {{key, value, datasource_alias, test_envs}}。"
            sql = row.get("value")
            if cls.is_empty_value(sql):
                continue
            datasource_alias = row.get("datasource_alias") or row.get("datasource_alias_id")
            if datasource_alias in [None, "", "null", "undefined"]:
                return (
                    f"{field_name}[{index}] 已配置 SQL，但未选择数据库类型。"
                    "请先调用 list_data_factory_datasource_aliases(project_product_id) 查询逻辑数据库，"
                    "必要时调用 list_data_factory_datasource_bindings(project_product_id, environment) 确认环境绑定，"
                    "然后在 SQL 项中写入 datasource_alias。"
                )
        return None

    @classmethod
    def validate_sql_datasources(
            cls,
            front_sql: Any = None,
            posterior_sql: Any = None,
            prefix: str = "",
    ) -> str | None:
        front_error = cls.validate_sql_rows_datasource_alias(front_sql, f"{prefix}front_sql")
        if front_error:
            return front_error
        return cls.validate_sql_rows_datasource_alias(posterior_sql, f"{prefix}posterior_sql")
