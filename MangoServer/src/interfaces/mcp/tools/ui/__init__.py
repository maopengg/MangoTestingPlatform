from __future__ import annotations

from .agent_execution import register_agent_ui_execution_tools
from .auth_config import register_ui_auth_config_tools
from .case import register_case_tools
from .delete import register_delete_tools
from .element import register_element_tools
from .method import register_method_tools
from .page import register_page_tools
from .page_step import register_page_step_tools
from .playwright_import import register_playwright_import_tools
from .public_variable import register_public_variable_tools
from .schema import register_schema_tools


def register_ui_tools(mcp):
    register_agent_ui_execution_tools(mcp)
    register_schema_tools(mcp)
    register_public_variable_tools(mcp)
    register_method_tools(mcp)
    register_page_tools(mcp)
    register_element_tools(mcp)
    register_page_step_tools(mcp)
    register_playwright_import_tools(mcp)
    register_case_tools(mcp)
    register_delete_tools(mcp)
    register_ui_auth_config_tools(mcp)
