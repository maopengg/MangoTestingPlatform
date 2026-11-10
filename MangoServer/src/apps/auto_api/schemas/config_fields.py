# -*- coding: utf-8 -*-
from copy import deepcopy

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum

API_INFO_CONFIG_DEFAULTS = {
    'url': '',
    'method': 0,
    'protocol_type': ApiProtocolTypeEnum.HTTP.value,
    'headers': None,
    'params': None,
    'is_text_params': 1,
    'body_type': ApiBodyTypeEnum.NONE.value,
    'body_config': None,
    'sse_config': None,
    'mcp_config': None,
    'posterior_json_path': [],
    'posterior_re': [],
    'posterior_func': None,
    'status': 2,
    'mcp_binding': None,
    'grpc_binding': None,
}

API_INFO_CONFIG_FIELDS = tuple(API_INFO_CONFIG_DEFAULTS.keys())
API_INFO_IDENTITY_FIELDS = ('id', 'name', 'project_product_id', 'module_id')

API_CASE_CONFIG_DEFAULTS = {
    'resource_cleanup': [],
    'callback_checks': [],
    'front_custom': [],
    'front_sql': [],
    'front_headers': [],
    'front_public': [],
    'front_auth_config': [],
    'posterior_sql': [],
}

API_CASE_CONFIG_FIELDS = tuple(API_CASE_CONFIG_DEFAULTS.keys())


def default_api_info_config() -> dict:
    return {field: deepcopy(default) for field, default in API_INFO_CONFIG_DEFAULTS.items()}


def default_api_case_config() -> dict:
    return {field: deepcopy(default) for field, default in API_CASE_CONFIG_DEFAULTS.items()}
