# -*- coding: utf-8 -*-
from typing import Any

from src.common.exceptions import ApiError, ERROR_MSG_0066


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
        raise ApiError(*ERROR_MSG_0066, value=(json_value_type(value),))
    return value
