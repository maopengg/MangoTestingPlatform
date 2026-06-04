from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rest_framework import serializers


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


class ApiRequestFileItem(StrictSchema):
    key: str = ''
    value: Any = ''


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
        try:
            return [ApiRequestFileItem.model_validate(item).model_dump() for item in value]
        except ValidationError as error:
            raise serializers.ValidationError(error.errors()) from error
    raise serializers.ValidationError(f'{field_name} 必须是对象、数组或空')
