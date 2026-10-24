from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND, AutoApiError
from src.interfaces.mcp.tools.api.auth_config import (
    _get_api_auth_config,
    register_api_auth_config_tools,
)


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class ApiAuthConfigMcpErrorTests(SimpleTestCase):
    @patch('src.apps.auto_api.services.api_auth_config.ApiAuthConfigService.get_instance')
    def test_missing_auth_config_is_converted_to_domain_error(self, get_instance):
        get_instance.side_effect = AutoApiError(API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND)

        with self.assertRaisesMessage(
                AutoApiError,
                'API授权配置不存在或已删除，请使用存在的授权配置ID查询',
        ):
            _get_api_auth_config(999999)

    def test_read_tools_return_not_found_business_error(self):
        registry = ToolRegistry()
        register_api_auth_config_tools(registry)
        error = AutoApiError(
            API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND,
            details={"auth_config_id": 999999},
        )

        for tool_name in (
                'get_api_auth_config_detail',
                'preview_clear_api_auth_config_cache_impact',
                'preview_delete_api_auth_config_impact',
        ):
            with self.subTest(tool=tool_name), patch(
                    'src.interfaces.mcp.tools.api.auth_config._get_api_auth_config',
                    side_effect=error,
            ), self.assertRaises(AutoApiError):
                registry.tools[tool_name](999999)
