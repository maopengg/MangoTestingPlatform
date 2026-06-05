# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段类型转换

import json
from datetime import date, datetime
from decimal import Decimal

from src.common.exceptions import ToolsError


class DataFactoryTypeCast:
    JS_MAX_SAFE_INTEGER = 9007199254740991

    @classmethod
    def cast(cls, value, platform_type: str):
        if value is None:
            return None
        try:
            if platform_type == "integer":
                return int(value)
            if platform_type == "decimal":
                return Decimal(str(value))
            if platform_type == "string":
                return str(value)
            if platform_type == "boolean":
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ["true", "1", "yes", "y"]
            if platform_type == "datetime":
                if isinstance(value, datetime):
                    return value
                return datetime.fromisoformat(str(value))
            if platform_type == "date":
                if isinstance(value, date):
                    return value
                return date.fromisoformat(str(value))
            if platform_type == "json":
                if isinstance(value, (dict, list)):
                    return value
                return json.loads(value)
            if platform_type == "enum":
                return str(value)
            return value
        except Exception as error:
            raise ToolsError(300, f"字段值类型转换失败：{value} -> {platform_type}") from error

    @classmethod
    def to_jsonable(cls, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, int) and not isinstance(value, bool):
            if abs(value) > cls.JS_MAX_SAFE_INTEGER:
                return str(value)
            return value
        if isinstance(value, dict):
            return {key: cls.to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.to_jsonable(item) for item in value]
        return value
