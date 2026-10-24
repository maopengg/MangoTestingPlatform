"""API Case MCP 工具注册门面。"""

from .case_tools.complete import register_case_complete_tools
from .case_tools.crud import register_case_crud_tools
from .case_tools.execution import register_case_execution_tools
from .case_tools.revision import register_case_revision_tools


def register_case_tools(mcp):
    register_case_revision_tools(mcp)
    register_case_crud_tools(mcp)
    register_case_complete_tools(mcp)
    register_case_execution_tools(mcp)
