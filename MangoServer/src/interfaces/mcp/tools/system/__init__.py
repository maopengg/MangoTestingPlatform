from __future__ import annotations

from .file import register_system_file_tools
from .variable import register_system_variable_tools


def register_system_tools(mcp):
    register_system_variable_tools(mcp)
    register_system_file_tools(mcp)
