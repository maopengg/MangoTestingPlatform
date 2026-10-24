# -*- coding: utf-8 -*-
import re

from src.apps.ai.models import AiMcpServer, AiMcpTool
from src.apps.ai.services.agent.mcp.registry import AgentMcpRegistry
from src.apps.ai.services.agent.mcp.tool_filter import AgentMcpToolFilter


class ApiAutomationToolSchemaBuilder:
    @classmethod
    def build_tools(
            cls,
            servers: list[AiMcpServer],
            user_id: int | None,
            existing_api_case_id: int | None,
            tool_limit: int | None = None,
            *,
            refresh: bool = False,
    ) -> tuple[list[dict], dict[str, AiMcpTool]]:
        raw_tools = AgentMcpRegistry.load_tools(
            [server.id for server in servers],
            user_id,
            refresh=refresh,
        )
        filtered = AgentMcpToolFilter.filter_for_api_automation(raw_tools, existing_api_case_id)
        used_names: set[str] = set()
        tools: list[dict] = []
        tool_map: dict[str, AiMcpTool] = {}
        selected_tools = filtered[:tool_limit] if tool_limit else filtered
        for tool in selected_tools:
            safe_name = cls.safe_tool_name(tool.name, used_names)
            tool_map[safe_name] = tool
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": safe_name,
                        "description": (tool.description or tool.title or tool.name)[:1200],
                        "parameters": tool.input_schema or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools, tool_map

    @staticmethod
    def safe_tool_name(name: str, used_names: set[str]) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name or "mcp_tool")[:64] or "mcp_tool"
        candidate = safe_name
        index = 1
        while candidate in used_names:
            suffix = f"_{index}"
            candidate = f"{safe_name[:64 - len(suffix)]}{suffix}"
            index += 1
        used_names.add(candidate)
        return candidate
