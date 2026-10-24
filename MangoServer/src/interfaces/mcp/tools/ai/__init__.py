from __future__ import annotations

from .query import register_ai_query_tools


def register_ai_tools(mcp):
    register_ai_query_tools(mcp)
