from __future__ import annotations

from .case_config import register_case_config_tools
from .datasource import register_datasource_tools
from .entity import register_entity_tools
from .execution import register_execution_tools
from .field import register_field_tools
from .schema import register_schema_tools
from .template import register_template_tools


def register_data_factory_tools(mcp):
    register_datasource_tools(mcp)
    register_entity_tools(mcp)
    register_field_tools(mcp)
    register_template_tools(mcp)
    register_case_config_tools(mcp)
    register_execution_tools(mcp)
    register_schema_tools(mcp)
