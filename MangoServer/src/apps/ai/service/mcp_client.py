# -*- coding: utf-8 -*-
import asyncio
from datetime import timedelta
from typing import Any

from asgiref.sync import async_to_sync
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.apps.ai.models import AiMcpServer
from src.apps.user.models import User
from src.common.enums.ai_enum import AiMcpAuthTypeEnum, AiMcpTransportTypeEnum


class ExternalMcpClient:
    @classmethod
    def headers(cls, server: AiMcpServer, user_id: int | None = None) -> dict[str, str]:
        config = server.auth_config or {}
        if server.auth_type == AiMcpAuthTypeEnum.BEARER.value:
            token = config.get("token") or config.get("api_key") or config.get("value")
            if not token and config.get("use_current_user_api_key") and user_id:
                user = User.objects.filter(id=user_id).first()
                if user and not user.api_key:
                    user.api_key = User.unique_api_key()
                    user.save(update_fields=["api_key"])
                token = user.api_key if user else None
            return {"Authorization": f"Bearer {token}"} if token else {}
        if server.auth_type == AiMcpAuthTypeEnum.API_KEY.value:
            header_name = config.get("header_name") or "Authorization"
            value = config.get("api_key") or config.get("token") or config.get("value")
            prefix = config.get("prefix", "")
            if value and prefix:
                value = f"{prefix} {value}"
            return {header_name: value} if value else {}
        return {}

    @classmethod
    def list_capabilities(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        return async_to_sync(cls._list_capabilities)(server, user_id)

    @classmethod
    def call_tool(cls, server: AiMcpServer, tool_name: str, arguments: dict | None = None, user_id: int | None = None) -> dict:
        return async_to_sync(cls._call_tool)(server, tool_name, arguments or {}, user_id)

    @classmethod
    async def _open_session(cls, server: AiMcpServer, user_id: int | None = None):
        if server.transport_type != AiMcpTransportTypeEnum.STREAMABLE_HTTP.value:
            raise ValueError("第一阶段通用外部 MCP 仅支持 streamable_http")
        return streamablehttp_client(
            server.server_url,
            headers=cls.headers(server, user_id),
            timeout=timedelta(seconds=30),
            sse_read_timeout=timedelta(seconds=60),
        )

    @classmethod
    async def _list_capabilities(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        async with await cls._open_session(server, user_id) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream, read_timeout_seconds=timedelta(seconds=60)) as session:
                initialize_result = await session.initialize()
                tools = await cls._safe_list(session.list_tools)
                resources = await cls._safe_list(session.list_resources)
                prompts = await cls._safe_list(session.list_prompts)
                return {
                    "initialize": cls._dump_model(initialize_result),
                    "tools": [cls._dump_model(item) for item in tools],
                    "resources": [cls._dump_model(item) for item in resources],
                    "prompts": [cls._dump_model(item) for item in prompts],
                }

    @classmethod
    async def _call_tool(cls, server: AiMcpServer, tool_name: str, arguments: dict, user_id: int | None = None) -> dict:
        async with await cls._open_session(server, user_id) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream, read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return cls._dump_model(result)

    @staticmethod
    async def _safe_list(method) -> list:
        try:
            result = await method()
        except Exception:
            return []
        if hasattr(result, "tools"):
            return list(result.tools or [])
        if hasattr(result, "resources"):
            return list(result.resources or [])
        if hasattr(result, "prompts"):
            return list(result.prompts or [])
        return []

    @staticmethod
    def _dump_model(value: Any) -> dict:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", by_alias=True, exclude_none=True)
        if isinstance(value, dict):
            return value
        return {"value": str(value)}
