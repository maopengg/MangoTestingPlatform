from typing import Any

from pydantic import BaseModel, Field, ValidationError
from rest_framework import serializers

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck
from src.apps.auto_api.exceptions import (
    API_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
    AUTO_API_CASE_SCHEMA_INVALID,
    AUTO_API_CASE_SCHEMA_DATABASE_TYPE_EXECUTION_UNSUPPORTED,
    AUTO_API_CASE_SCHEMA_INVALID_CODE_INVALID,
    AUTO_API_CASE_SCHEMA_EXECUTION_INVALID,
    AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_PARAMETER_INVALID,
    AUTO_API_CASE_SCHEMA_DATABASE_NOT_FOUND,
    AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_DATABASE_INVALID,
    AUTO_API_CASE_SCHEMA_DATABASE_INVALID,
    AUTO_API_CASE_SCHEMA_EXECUTION_INVALID_CODE_EXECUTION_INVALID,
    AUTO_API_CASE_SCHEMA_ITEM_INVALID,
    AUTO_API_CASE_EXECUTION_CONTENT_STRING_REQUIRED,
    AUTO_API_CASE_SCHEMA_JSON_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.common.schemas import StrictSchema

DEFAULT_RAW_CONTENT_TYPE = 'application/json'


def validate_test_environment(value) -> int:
    if isinstance(value, (bool, float)) or value is None or value == '':
        raise AutoApiError(API_TEST_ENVIRONMENT_EXECUTION_REQUIRED)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized.isdigit():
            raise AutoApiError(API_TEST_ENVIRONMENT_EXECUTION_REQUIRED)
        value = normalized
    try:
        test_env = int(value)
    except (TypeError, ValueError) as error:
        raise AutoApiError(API_TEST_ENVIRONMENT_EXECUTION_REQUIRED, error=str(error)) from error
    if test_env not in EnvironmentEnum.get_key_list():
        raise AutoApiError(API_TEST_ENVIRONMENT_EXECUTION_REQUIRED)
    return test_env


class ApiKeyValueItem(StrictSchema):
    key: str = ''
    value: str = ''
    datasource_alias: int | None = None


class ApiEnvironmentKeyValueItem(ApiKeyValueItem):
    test_envs: list[int] = Field(default_factory=list)


class ApiElasticsearchOperationConfig(StrictSchema):
    index: str = Field(min_length=1)
    query: dict[str, Any]


class ApiDataSourceOperationItem(ApiKeyValueItem):
    datasource_alias: int = Field(gt=0)
    value: str | ApiElasticsearchOperationConfig
    test_envs: list[int] = Field(default_factory=list)


class ApiParametrizeItem(StrictSchema):
    key: str = ''
    value: Any = None
    test_envs: list[int] = Field(default_factory=list)


class ApiParametrizeSuite(StrictSchema):
    name: str = ''
    parametrize: list[ApiParametrizeItem] = Field(default_factory=list)


class ApiJsonPathAssertionItem(StrictSchema):
    assertion_type: str = 'jsonpath'
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
    test_envs: list[int] = Field(default_factory=list)


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
    project_product: Any = None


def validate_body_config(value: Any, field_name: str):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise serializers.ValidationError(f'{field_name} 必须是JSON对象')
    return value


def merge_scenario_protocol_config(
        body_config: Any,
        mcp_config: Any = None,
        grpc_config: Any = None,
        protocol_expectation: Any = None,
) -> dict | None:
    """Fold scenario protocol execution config into body_config.

    ApiCaseDetailedParameter no longer stores mcp_config/grpc_config as
    independent columns. Old callers may still send those keys during the
    transition, so normalize them into body_config before persistence.
    """
    if protocol_expectation is None and isinstance(body_config, dict):
        protocol_expectation = body_config.get('protocol_expectation')
    if mcp_config in (None, '') and grpc_config in (None, '') and protocol_expectation in (None, ''):
        return body_config
    body = dict(body_config or {}) if isinstance(body_config, dict) else {}
    if mcp_config not in (None, ''):
        if not isinstance(mcp_config, dict):
            raise serializers.ValidationError('MCP配置必须是JSON对象')
        body['mcp_config'] = mcp_config
    if grpc_config not in (None, ''):
        if not isinstance(grpc_config, dict):
            raise serializers.ValidationError('gRPC配置必须是JSON对象')
        body['grpc_config'] = grpc_config
    if protocol_expectation not in (None, ''):
        if not isinstance(protocol_expectation, dict):
            raise serializers.ValidationError('预期调用结果必须是JSON对象')
        mode = str(protocol_expectation.get('mode') or 'auto').lower()
        if mode not in {'auto', 'success', 'codes', 'any'}:
            raise serializers.ValidationError('预期调用结果只支持自动判断、正常成功、指定状态码或任意状态')
        status_codes = protocol_expectation.get('status_codes') or []
        if mode == 'codes':
            if not isinstance(status_codes, list) or not status_codes:
                raise serializers.ValidationError('指定状态码模式至少需要填写一个HTTP状态码')
            try:
                status_codes = sorted({int(code) for code in status_codes})
            except (TypeError, ValueError):
                raise serializers.ValidationError('HTTP状态码必须是整数')
            if any(code < 100 or code > 599 for code in status_codes):
                raise serializers.ValidationError('HTTP状态码必须在100到599之间')
        else:
            status_codes = []
        body['protocol_expectation'] = {
            'mode': mode,
            'status_codes': status_codes,
        }
        if 'inherit_system' in protocol_expectation:
            inherit_system = protocol_expectation['inherit_system']
            checks = protocol_expectation.get('checks', [])
            if type(inherit_system) is not bool or not isinstance(checks, list) or any(
                    not isinstance(check, str) or check not in {item.value for item in ApiDefaultAssertionCheck}
                    for check in checks):
                raise serializers.ValidationError('协议断言需指定是否继承系统配置及已注册的检查项列表')
            body['protocol_expectation'] = {
                'mode': 'auto', 'status_codes': [],
                'inherit_system': inherit_system,
                'checks': [] if inherit_system else list(dict.fromkeys(checks)),
            }
    return body or None


def unpack_scenario_body_config(protocol_type: str | None, body_config: Any) -> tuple[Any, dict | None, dict | None]:
    if not isinstance(body_config, dict):
        return body_config, None, None
    protocol = str(protocol_type or '').lower()
    mcp_config = body_config.get('mcp_config') if isinstance(body_config.get('mcp_config'), dict) else None
    grpc_config = body_config.get('grpc_config') if isinstance(body_config.get('grpc_config'), dict) else None
    if protocol == 'mcp':
        if 'arguments' in body_config:
            return body_config.get('arguments'), mcp_config, grpc_config
        if 'body_config' in body_config:
            return body_config.get('body_config'), mcp_config, grpc_config
        return {
            key: value for key, value in body_config.items()
            if key not in {'mcp_config', 'protocol_expectation'}
        }, mcp_config, grpc_config
    if protocol == 'grpc':
        if 'source_type' in body_config and 'body' in body_config:
            return body_config.get('body'), mcp_config, grpc_config
        if 'request' in body_config:
            return body_config.get('request'), mcp_config, grpc_config
        if 'body_config' in body_config:
            return body_config.get('body_config'), mcp_config, grpc_config
        return {
            key: value for key, value in body_config.items()
            if key not in {'grpc_config', 'protocol_expectation'}
        }, mcp_config, grpc_config
    return {
        key: value for key, value in body_config.items()
        if key != 'protocol_expectation'
    }, mcp_config, grpc_config


def scenario_mcp_config(body_config: Any) -> dict:
    return (body_config or {}).get('mcp_config') or {} if isinstance(body_config, dict) else {}


def scenario_grpc_config(body_config: Any) -> dict:
    return (body_config or {}).get('grpc_config') or {} if isinstance(body_config, dict) else {}


def scenario_protocol_expectation(body_config: Any) -> dict:
    return (body_config or {}).get('protocol_expectation') or {} if isinstance(body_config, dict) else {}


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
    result = []
    for index, item in enumerate(value, start=1):
        try:
            validated = model.model_validate(item).model_dump()
        except ValidationError as error:
            messages = []
            for detail in error.errors(include_url=False, include_input=False):
                location = '.'.join(str(part) for part in detail.get('loc') or ()) or '配置'
                if detail.get('type') == 'extra_forbidden':
                    messages.append(f'不支持字段 {location}')
                else:
                    messages.append(f'{location}：{detail.get("msg") or "格式不正确"}')
            raise AutoApiError(
                AUTO_API_CASE_SCHEMA_ITEM_INVALID,
                value=(field_name, index, '；'.join(messages)),
            ) from error
        result.append(normalize_config_test_envs(validated, f'{field_name}第{index}项'))
    return result


def normalize_config_test_envs(value: Any, field_name: str) -> Any:
    valid_envs = set(EnvironmentEnum.get_key_list())
    if isinstance(value, list):
        return [
            normalize_config_test_envs(item, f'{field_name}第{index}项')
            for index, item in enumerate(value, start=1)
        ]
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if 'test_envs' in result:
        test_envs = result.get('test_envs') or []
        if not isinstance(test_envs, list):
            raise serializers.ValidationError(f'{field_name}的适用环境必须是数组')
        normalized_envs = []
        for test_env in test_envs:
            if isinstance(test_env, bool) or not isinstance(test_env, int) or test_env not in valid_envs:
                raise serializers.ValidationError(f'{field_name}包含无效适用环境：{test_env}')
            if test_env not in normalized_envs:
                normalized_envs.append(test_env)
        result['test_envs'] = normalized_envs
    for key, item in list(result.items()):
        if key != 'test_envs':
            result[key] = normalize_config_test_envs(item, f'{field_name}.{key}')
    return result


def validate_data_source_operation_list(
        value: Any,
        field_name: str,
        project_product_id: int | str | None = None,
) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise AutoApiError(AUTO_API_CASE_SCHEMA_INVALID, value=(field_name,))

    valid_envs = set(EnvironmentEnum.get_key_list())
    result = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise AutoApiError(AUTO_API_CASE_SCHEMA_INVALID_CODE_INVALID, value=(field_name, index))
        test_envs = item.get('test_envs')
        if test_envs is None:
            test_envs = []
        if not isinstance(test_envs, list):
            raise AutoApiError(AUTO_API_CASE_SCHEMA_EXECUTION_INVALID, value=(field_name, index))

        normalized_envs = []
        for test_env in test_envs:
            if isinstance(test_env, bool) or not isinstance(test_env, int) or test_env not in valid_envs:
                raise AutoApiError(AUTO_API_CASE_SCHEMA_EXECUTION_INVALID_CODE_EXECUTION_INVALID,
                                   value=(field_name, index, test_env))
            if test_env not in normalized_envs:
                normalized_envs.append(test_env)

        normalized_item = dict(item)
        normalized_item['test_envs'] = normalized_envs
        try:
            result.append(ApiDataSourceOperationItem.model_validate(normalized_item).model_dump())
        except ValidationError as error:
            raise AutoApiError(AUTO_API_CASE_SCHEMA_ITEM_INVALID, value=(field_name, index, error)) from error
    if not result:
        return result

    from src.apps.data_factory.models import DataFactoryDatasourceAlias
    from src.apps.test_center.enums.data_source import DataSourceTypeEnum
    from mangotools.enums import StatusEnum

    alias_ids = {item['datasource_alias'] for item in result}
    aliases = {
        item.id: item
        for item in DataFactoryDatasourceAlias.objects.filter(id__in=alias_ids)
    }
    try:
        normalized_product_id = int(project_product_id) if project_product_id not in [None, ''] else None
    except (TypeError, ValueError) as error:
        raise AutoApiError(AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_PARAMETER_INVALID, value=(field_name,)) from error

    from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService

    relational_types = DataSourceExecutionService.EXECUTABLE_RELATIONAL_TYPES
    for index, item in enumerate(result, start=1):
        alias = aliases.get(item['datasource_alias'])
        if not alias:
            raise AutoApiError(AUTO_API_CASE_SCHEMA_DATABASE_NOT_FOUND, value=(field_name, index))
        if normalized_product_id is not None and alias.project_product_id != normalized_product_id:
            raise AutoApiError(AUTO_API_CASE_SCHEMA_PROJECT_PRODUCT_DATABASE_INVALID, value=(field_name, index))
        if alias.status != StatusEnum.SUCCESS.value:
            raise AutoApiError(AUTO_API_CASE_SCHEMA_DATABASE_INVALID, value=(field_name, index))

        operation_value = item['value']
        if alias.db_type in relational_types or alias.db_type == DataSourceTypeEnum.REDIS.value:
            if not isinstance(operation_value, str) or not operation_value.strip():
                type_name = DataSourceTypeEnum.obj().get(alias.db_type, alias.db_type)
                raise AutoApiError(AUTO_API_CASE_EXECUTION_CONTENT_STRING_REQUIRED,
                                   value=(field_name, index, type_name))
            continue
        if alias.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            if not isinstance(operation_value, dict):
                raise AutoApiError(AUTO_API_CASE_SCHEMA_JSON_EXECUTION_INVALID, value=(field_name, index))
            continue
        type_name = DataSourceTypeEnum.obj().get(alias.db_type, alias.db_type)
        raise AutoApiError(AUTO_API_CASE_SCHEMA_DATABASE_TYPE_EXECUTION_UNSUPPORTED,
                           value=(field_name, index, type_name))
    return result


def validate_sql_item_list(
        value: Any,
        field_name: str,
        project_product_id: int | str | None = None,
) -> list[dict]:
    """兼容历史调用；新代码统一使用数据库操作命名。"""
    return validate_data_source_operation_list(value, field_name, project_product_id)


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


def validate_scenario_tag_list(value: Any, field_name: str = '执行场景') -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f'{field_name} 必须是数组')
    allowed = set(ApiCaseScenarioTagEnum.get_key_list())
    normalized = []
    for item in value:
        if not isinstance(item, str) or item not in allowed:
            raise serializers.ValidationError(f'{field_name}包含不支持的标签：{item}')
        if item not in normalized:
            normalized.append(item)
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
