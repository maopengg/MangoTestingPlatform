from __future__ import annotations

from .task import register_scheduled_task_tools as register_scheduled_task_domain_tools


def register_scheduled_task_tools(mcp):
    register_scheduled_task_domain_tools(mcp)
