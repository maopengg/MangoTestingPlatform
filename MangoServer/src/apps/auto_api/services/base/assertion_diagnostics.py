# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Iterable

from deepdiff import DeepDiff
from itertools import zip_longest

MAX_PREVIEW_LENGTH = 300


def value_type_name(value: Any) -> str:
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


def value_preview(value: Any, max_length: int = MAX_PREVIEW_LENGTH) -> str:
    if isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        text = str(value)
    if len(text) > max_length:
        return f'{text[:max_length]}...（共{len(text)}字符）'
    return text


def typed_value(value: Any) -> str:
    return f'{value_preview(value)}({type(value).__name__})'


def sql_preview(sql: Any) -> str:
    text = ' '.join(str(sql or '').split())
    return value_preview(text)


def json_path(path: Iterable[Any] | None) -> str:
    result = '$'
    for part in path or []:
        if isinstance(part, int):
            result += f'[{part}]'
        elif re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', str(part)):
            result += f'.{part}'
        else:
            result += f'[{json.dumps(str(part), ensure_ascii=False)}]'
    return result


def deepdiff_path(path: str) -> str:
    if not path or path == 'root':
        return '$'
    normalized = '$' + path[len('root'):]
    return re.sub(r"\['([A-Za-z_][A-Za-z0-9_]*)'\]", r'.\1', normalized)


def _filter_json_to_expected(actual: Any, expect: Any) -> Any:
    if isinstance(actual, dict) and isinstance(expect, dict):
        return {
            key: _filter_json_to_expected(actual[key], expect_value)
            for key, expect_value in expect.items()
            if key in actual
        }
    if isinstance(actual, list) and isinstance(expect, list) and expect and isinstance(expect[0], dict):
        template = expect[0]
        return [
            _filter_json_to_expected(item, template) if isinstance(item, dict) else item
            for item in actual
        ]
    return actual


def describe_json_consistency(actual: Any, expect: Any, limit: int = 5) -> str | None:
    filtered_actual = _filter_json_to_expected(actual, expect)
    differences = DeepDiff(filtered_actual, expect, ignore_order=True, view='tree')
    if not differences:
        return None
    messages = []
    category_titles = {
        'dictionary_item_added': '响应中缺少路径',
        'iterable_item_added': '响应数组中缺少内容',
        'dictionary_item_removed': '响应中存在未预期路径',
        'iterable_item_removed': '响应数组中存在未预期内容',
    }
    for category, changes in differences.items():
        for change in changes:
            path = deepdiff_path(change.path())
            if category == 'values_changed':
                messages.append(
                    f'路径【{path}】值不一致，实际={typed_value(change.t1)}，预期={typed_value(change.t2)}'
                )
            elif category == 'type_changes':
                messages.append(
                    f'路径【{path}】类型不一致，实际={typed_value(change.t1)}，预期={typed_value(change.t2)}'
                )
            elif category in category_titles:
                messages.append(f'{category_titles[category]}【{path}】')
            else:
                messages.append(f'路径【{path}】不符合预期，差异类型：{category}')
            if len(messages) >= limit:
                break
        if len(messages) >= limit:
            break
    if not messages:
        return '响应JSON与预期JSON不一致'
    difference_count = sum(len(changes) for changes in differences.values())
    suffix = f'；其余{difference_count - len(messages)}处差异请在断言详情中查看' if difference_count > len(
        messages) else ''
    return '；'.join(messages) + suffix


def first_text_difference(actual: str, expect: str) -> int | None:
    for index, (actual_char, expect_char) in enumerate(zip_longest(actual, expect, fillvalue=None), start=1):
        if actual_char != expect_char:
            return index
    return None


def describe_schema_validation(error) -> str:
    path = json_path(error.absolute_path)
    validator = error.validator
    if validator == 'required':
        match = re.search(r"'(.+)' is a required property", error.message)
        field = match.group(1) if match else error.message
        return f'响应路径【{path}】缺少必填字段【{field}】'
    if validator == 'type':
        return (
            f'响应路径【{path}】类型为【{value_type_name(error.instance)}】，'
            f'Schema要求类型为【{error.validator_value}】'
        )
    if validator == 'enum':
        return (
            f'响应路径【{path}】实际值【{value_preview(error.instance)}】不在允许值'
            f'【{value_preview(error.validator_value)}】中'
        )
    if validator == 'additionalProperties':
        return f'响应路径【{path}】包含Schema未允许的字段：{error.message}'
    if validator in {'minimum', 'exclusiveMinimum'}:
        return f'响应路径【{path}】实际值【{value_preview(error.instance)}】小于允许的最小值【{error.validator_value}】'
    if validator in {'maximum', 'exclusiveMaximum'}:
        return f'响应路径【{path}】实际值【{value_preview(error.instance)}】大于允许的最大值【{error.validator_value}】'
    if validator == 'pattern':
        return f'响应路径【{path}】实际值未匹配正则表达式【{error.validator_value}】'
    return f'响应路径【{path}】校验失败：{error.message}'


def describe_schema_config(error) -> str:
    return f'Schema路径【{json_path(error.absolute_schema_path)}】配置不合法：{error.message}'
