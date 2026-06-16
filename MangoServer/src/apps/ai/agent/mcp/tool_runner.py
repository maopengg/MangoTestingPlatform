# -*- coding: utf-8 -*-
from src.apps.ai.service.core import McpService


class AgentMcpToolRunner:
    @staticmethod
    def call(task, tool, arguments: dict | None = None, user_id: int | None = None):
        result = McpService.call_tool(tool.server, tool.name, arguments or {}, user_id)
        McpService.log_tool_call(task, tool.name, arguments or {}, result, tool.server)
        return result
