"""定时任务 MCP 工具注册门面。"""

from .task_tools.binding import register_scheduled_task_binding_tools
from .task_tools.catalog import register_scheduled_task_catalog_tools
from .task_tools.query import register_scheduled_task_query_tools
from .task_tools.trigger import register_scheduled_task_trigger_tools


def register_scheduled_task_tools(mcp):
    register_scheduled_task_catalog_tools(mcp)
    register_scheduled_task_query_tools(mcp)
    register_scheduled_task_trigger_tools(mcp)
    register_scheduled_task_binding_tools(mcp)
