# -*- coding: utf-8 -*-
import hashlib
import json

from django.utils import timezone

from src.apps.ai.enums import AiMcpStatusEnum
from src.apps.ai.models import AiMcpServer, AiMcpTool
from src.apps.ai.services.core import McpService


class AgentMcpRegistry:
    @staticmethod
    def load_servers(server_ids: list[int]) -> list[AiMcpServer]:
        return list(AiMcpServer.objects.filter(id__in=server_ids, status=AiMcpStatusEnum.ENABLED.value))

    @staticmethod
    def load_tools(
            server_ids: list[int],
            user_id: int | None = None,
            *,
            refresh: bool = False,
    ) -> list[AiMcpTool]:
        servers = AgentMcpRegistry.load_servers(server_ids)
        for server in servers:
            if refresh or not AiMcpTool.objects.filter(server=server, tool_type="tool", enabled=True).exists():
                McpService.sync_tools(server, user_id)
        return list(
            AiMcpTool.objects.filter(
                server_id__in=[server.id for server in servers],
                tool_type="tool",
                enabled=True,
            ).select_related("server")
        )

    @staticmethod
    def capability_snapshot(servers: list[AiMcpServer], tools: list[AiMcpTool]) -> dict:
        tools_by_server: dict[int, list[AiMcpTool]] = {}
        for tool in tools:
            tools_by_server.setdefault(tool.server_id, []).append(tool)
        snapshots = []
        for server in servers:
            rows = []
            for tool in sorted(tools_by_server.get(server.id, []), key=lambda item: item.name):
                schema_raw = json.dumps(tool.input_schema or {}, ensure_ascii=False, sort_keys=True, default=str)
                rows.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "schema_hash": hashlib.sha256(schema_raw.encode("utf-8")).hexdigest(),
                        "risk_level": tool.risk_level,
                        "write_operation": tool.write_operation,
                    }
                )
            list_raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
            snapshots.append(
                {
                    "id": server.id,
                    "name": server.name,
                    "prompt": server.prompt or "",
                    "tool_list_hash": hashlib.sha256(list_raw.encode("utf-8")).hexdigest(),
                    "last_verified_at": timezone.now().isoformat(),
                    "tools": rows,
                }
            )
        return {"servers": snapshots}
