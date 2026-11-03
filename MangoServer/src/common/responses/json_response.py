# -*- coding: utf-8 -*-
import re
from typing import Any

from mangotools.data_processor import JsonTool
from mangotools.exceptions import MangoToolsError

from src.common.exceptions import (
    CommonError,
    JSONPATH_OPERATION_FAILED,
    JSONPATH_VALUE_TYPE_UNSUPPORTED,
)

JSONPATH_MISSING_FIELD_PATTERN = re.compile(
    r'表达式[:：]?【(?P<expression>.+?)】[。；;，, ]*'
    r'路径【(?P<parent>.+?)】下不存在字段【(?P<field>.+?)】[；;，, ]*'
    r'当前对象可用字段[:：]?\s*(?P<fields>.+)'
)


def json_value_type(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, (int, float)):
        return 'number'
    return type(value).__name__


def is_jsonpath_source(value: Any) -> bool:
    return isinstance(value, (dict, list))


def ensure_jsonpath_source(value: Any):
    if not is_jsonpath_source(value):
        raise CommonError(JSONPATH_VALUE_TYPE_UNSUPPORTED, value=(json_value_type(value),))
    return value


def improve_jsonpath_error_message(message: str) -> str:
    missing_field_match = JSONPATH_MISSING_FIELD_PATTERN.search(message)
    if not missing_field_match:
        return message
    expression = missing_field_match.group('expression')
    parent = missing_field_match.group('parent')
    field = missing_field_match.group('field')
    fields = missing_field_match.group('fields')
    return (
        f'JSONPath字段不存在：表达式【{expression}】已定位到父路径【{parent}】，'
        f'但该对象没有字段【{field}】。当前对象可用字段：{fields}。'
        '请将断言字段改为可用字段之一，或检查接口返回是否确实应该包含该字段。'
    )


def extract_jsonpath_value(
        source: dict | list,
        expression: str,
        *,
        operation: str,
        cache_key: str | None = None,
):
    """Read JSONPath data and add the business operation that failed."""
    try:
        JsonTool.validate_json_path_expression(expression)
        ensure_jsonpath_source(source)
        return JsonTool.get_json_path_value(source, expression)
    except MangoToolsError as error:
        key_context = f'，目标缓存Key：【{cache_key}】' if cache_key else ''
        message = improve_jsonpath_error_message(error.msg)
        raise CommonError(
            JSONPATH_OPERATION_FAILED,
            value=(operation, key_context, message),
        ) from error
