# -*- coding: utf-8 -*-
from src.apps.ai.models import AiMcpServer, AiMcpTool
from src.apps.ai.service.core import McpService
from src.common.enums.ai_enum import AiMcpStatusEnum


class AgentMcpRegistry:
    @staticmethod
    def load_servers(server_ids: list[int]) -> list[AiMcpServer]:
        return list(AiMcpServer.objects.filter(id__in=server_ids, status=AiMcpStatusEnum.ENABLED.value))

    @staticmethod
    def load_tools(server_ids: list[int], user_id: int | None = None) -> list[AiMcpTool]:
        servers = AgentMcpRegistry.load_servers(server_ids)
        for server in servers:
            if not AiMcpTool.objects.filter(server=server, tool_type="tool", enabled=True).exists():
                McpService.sync_tools(server, user_id)
        return list(
            AiMcpTool.objects.filter(
                server_id__in=[server.id for server in servers],
                tool_type="tool",
                enabled=True,
            ).select_related("server")
        )
