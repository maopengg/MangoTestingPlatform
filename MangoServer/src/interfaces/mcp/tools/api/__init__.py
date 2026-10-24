from __future__ import annotations

from .api_info import register_api_info_tools
from .assertion import register_assertion_tools
from .auth_config import register_api_auth_config_tools
from .case import register_case_tools
from .delete import register_delete_tools
from .headers import register_headers_tools
from .module_coverage import register_module_coverage_tools
from .public_variable import register_public_variable_tools
from .scenario import register_scenario_tools
from .schema import register_schema_tools


def register_api_tools(mcp):
    register_module_coverage_tools(mcp)
    register_headers_tools(mcp)
    register_public_variable_tools(mcp)
    register_api_auth_config_tools(mcp)
    register_api_info_tools(mcp)
    register_case_tools(mcp)
    register_scenario_tools(mcp)
    register_assertion_tools(mcp)
    register_schema_tools(mcp)
    register_delete_tools(mcp)
