from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rest_framework import serializers

DEFAULT_RAW_CONTENT_TYPE = 'application/json'


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ApiKeyValueItem(StrictSchema):
    key: str = ''
    value: str = ''
    datasource_alias: int | None = None


class ApiParametrizeItem(StrictSchema):
    key: str = ''
    value: Any = None


class ApiParametrizeSuite(StrictSchema):
    name: str = ''
    parametrize: list[ApiParametrizeItem] = Field(default_factory=list)


class ApiJsonPathAssertionItem(StrictSchema):
    actual: str = ''
    method: str = ''
    expect: str | None = ''
    group_name: str = ''
    group_logic: str = 'AND'


class ApiSqlAssertionItem(StrictSchema):
    actual: str = ''
    method: str = ''
    expect: str = ''
    datasource_alias: int | None = None


class ApiGeneralAssertionParameter(StrictSchema):
    d: bool = False
    f: str = ''
    n: str = ''
    p: str = ''
    v: str = ''


class ApiGeneralAssertionValue(StrictSchema):
    label: str | None = None
    value: str = ''
    parameter: list[ApiGeneralAssertionParameter] = Field(default_factory=list)


class ApiGeneralAssertionItem(StrictSchema):
    method: str = ''
    value: ApiGeneralAssertionValue = Field(default_factory=ApiGeneralAssertionValue)
    group_name: str = ''
    group_logic: str = 'AND'


class ApiRequestFileItem(StrictSchema):
    key: str = ''
    value: Any = ''


class ApiMultipartFieldItem(StrictSchema):
    key: str = ''
    value: Any = ''


class ApiMultipartFileItem(StrictSchema):
    key: str = ''
    file_id: int
    file_name: str | None = None


def validate_body_config(value: Any, field_name: str):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise serializers.ValidationError(f'{field_name} 必须是JSON对象')
    return value


def normalize_body_config_by_type(body_type: str | None, body_config: Any) -> dict | None:
    config = validate_body_config(body_config, '请求体配置')
    if body_type == 'raw':
        config = dict(config or {})
        config['content_type'] = config.get('content_type') or DEFAULT_RAW_CONTENT_TYPE
        config['body_text'] = config.get('body_text') or ''
        return config
    return config


def build_body_from_legacy(
        data: Any = None,
        json_body: Any = None,
        file_payload: Any = None,
) -> tuple[str, dict | None]:
    if file_payload:
        return 'multipart', normalize_multipart_body_config(file_payload)
    if json_body not in [None, '']:
        if isinstance(json_body, str):
            return 'json', {'source_type': 'template', 'body_text': json_body}
        return 'json', {'source_type': 'value', 'body': json_body}
    if data not in [None, '']:
        if isinstance(data, str):
            return 'form', {'fields': legacy_mapping_to_fields(data)}
        if isinstance(data, dict):
            return 'form', {'fields': [{'key': key, 'value': value} for key, value in data.items()]}
        return 'raw', {'body_text': data, 'content_type': DEFAULT_RAW_CONTENT_TYPE}
    return 'none', None


def legacy_mapping_to_fields(value: Any) -> list[dict]:
    if value in [None, '']:
        return []
    if isinstance(value, dict):
        return [{'key': key, 'value': item} for key, item in value.items()]
    if isinstance(value, list):
        return value
    return [{'key': 'body', 'value': value}]


def normalize_multipart_body_config(value: Any) -> dict:
    if value in [None, '', {}, []]:
        return {'fields': [], 'files': []}
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        raise serializers.ValidationError('multipart 配置必须是数组')
    fields = []
    files = []
    for item in value:
        if not isinstance(item, dict):
            raise serializers.ValidationError('multipart 每一项必须是对象')
        if {'key', 'file_id'}.issubset(item.keys()):
            files.append(ApiMultipartFileItem.model_validate(item).model_dump())
            continue
        if set(item.keys()).issubset({'key', 'value'}) and item.get('key'):
            fields.append(ApiMultipartFieldItem.model_validate(item).model_dump())
            continue
        for key, item_value in item.items():
            if isinstance(item_value, dict) and item_value.get('file_id'):
                files.append({
                    'key': key,
                    'file_id': item_value.get('file_id'),
                    'file_name': item_value.get('file_name'),
                })
            else:
                fields.append({'key': key, 'value': item_value})
    return {'fields': fields, 'files': files}


def validate_model_list(
        value: Any,
        model: type[BaseModel],
        field_name: str,
        allow_none: bool = False,
        allow_empty_dict: bool = False,
) -> list:
    if value is None and allow_none:
        return value
    if value is None:
        return []
    if value == {} and allow_empty_dict:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f'{field_name} 必须是数组')
    try:
        return [model.model_validate(item).model_dump() for item in value]
    except ValidationError as error:
        raise serializers.ValidationError(error.errors()) from error


def validate_int_list(value: Any, field_name: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f'{field_name} 必须是数组')
    normalized = []
    for item in value:
        if isinstance(item, int):
            normalized.append(item)
            continue
        if isinstance(item, str) and item.isdigit():
            normalized.append(int(item))
            continue
        raise serializers.ValidationError(f'{field_name} 只能包含整数ID')
    return normalized


def validate_json_object(value: Any, field_name: str, allow_list: bool = False, allow_none: bool = True):
    if value is None and allow_none:
        return value
    valid_types = (dict, list) if allow_list else (dict,)
    if not isinstance(value, valid_types):
        type_name = '对象或数组' if allow_list else '对象'
        raise serializers.ValidationError(f'{field_name} 必须是JSON{type_name}')
    return value


def validate_file_payload(value: Any, field_name: str):
    if value is None:
        return value
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        normalized = []
        for item in value:
            if not isinstance(item, dict) or not item:
                raise serializers.ValidationError(f'{field_name} 必须是对象、数组或空')
            if set(item.keys()).issubset({'key', 'value'}) and item.get('key'):
                try:
                    file_item = ApiRequestFileItem.model_validate(item)
                except ValidationError as error:
                    raise serializers.ValidationError(error.errors()) from error
                normalized.append({file_item.key: file_item.value})
                continue
            if any(not key for key in item.keys()):
                raise serializers.ValidationError(f'{field_name} 中的请求文件字段名不能为空')
            normalized.append(item)
        return normalized
    raise serializers.ValidationError(f'{field_name} 必须是对象、数组或空')
