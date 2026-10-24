from __future__ import annotations

from .context import register_project_context_tools


def register_project_tools(mcp):
    register_project_context_tools(mcp)
