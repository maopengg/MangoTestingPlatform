# -*- coding: utf-8 -*-
from datetime import timedelta
from typing import Any

import httpx
from asgiref.sync import async_to_sync
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.apps.ai.enums import AiMcpAuthTypeEnum, AiMcpTransportTypeEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiMcpServer
from src.apps.user.models import User


class ExternalMcpClient:
    """统一的外部 MCP 传输客户端。

    平台自身的 MCP 管理能力和 API 自动化的 MCP 协议执行都使用这个类。
    """

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
    def list_capabilities_runtime(
            cls,
            *,
            server_url: str,
            transport_type: int,
            headers: dict | None,
            timeout_seconds: int = 60,
    ) -> dict:
        return async_to_sync(cls._list_capabilities_runtime)(
            server_url=server_url,
            transport_type=transport_type,
            headers=headers or {},
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def call_tool(cls, server: AiMcpServer, tool_name: str, arguments: dict | None = None,
                  user_id: int | None = None) -> dict:
        return async_to_sync(cls._call_tool)(server, tool_name, arguments or {}, user_id)

    @classmethod
    def call_tool_runtime(
            cls,
            *,
            server_url: str,
            transport_type: int,
            headers: dict | None,
            tool_name: str,
            arguments: dict | None = None,
            timeout_seconds: int = 60,
    ) -> dict:
        return async_to_sync(cls._call_tool_runtime)(
            server_url=server_url,
            transport_type=transport_type,
            headers=headers or {},
            tool_name=tool_name,
            arguments=arguments or {},
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    async def _open_session(cls, server: AiMcpServer, user_id: int | None = None):
        cls.ensure_supported_transport(server.transport_type)
        return streamablehttp_client(
            server.server_url,
            headers=cls.headers(server, user_id),
            timeout=timedelta(seconds=30),
            sse_read_timeout=timedelta(seconds=60),
            httpx_client_factory=cls.create_no_proxy_http_client,
        )

    @classmethod
    async def _list_capabilities(cls, server: AiMcpServer, user_id: int | None = None) -> dict:
        result = None
        try:
            async with await cls._open_session(server, user_id) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream,
                                         read_timeout_seconds=timedelta(seconds=60)) as session:
                    result = await cls._list_capabilities_from_session(session)
                    return result
        except Exception as exc:
            if result is not None and cls.is_session_close_error(exc):
                return result
            raise

    @classmethod
    async def _list_capabilities_runtime(
            cls,
            *,
            server_url: str,
            transport_type: int,
            headers: dict,
            timeout_seconds: int,
    ) -> dict:
        timeout = cls.runtime_timeout(timeout_seconds)
        result = None
        try:
            async with cls.runtime_transport_context(
                    server_url=server_url,
                    transport_type=transport_type,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=timeout) as session:
                    result = await cls._list_capabilities_from_session(session)
                    return result
        except Exception as exc:
            if result is not None and cls.is_session_close_error(exc):
                return result
            raise

    @classmethod
    async def _call_tool(cls, server: AiMcpServer, tool_name: str, arguments: dict, user_id: int | None = None) -> dict:
        data = None
        try:
            async with await cls._open_session(server, user_id) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream,
                                         read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    data = cls._dump_model(result)
                    return data
        except Exception as exc:
            if data is not None and cls.is_session_close_error(exc):
                return data
            raise

    @classmethod
    async def _call_tool_runtime(
            cls,
            *,
            server_url: str,
            transport_type: int,
            headers: dict,
            tool_name: str,
            arguments: dict,
            timeout_seconds: int,
    ) -> dict:
        timeout = cls.runtime_timeout(timeout_seconds)
        data = None
        try:
            async with cls.runtime_transport_context(
                    server_url=server_url,
                    transport_type=transport_type,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=timeout) as session:
                    initialize_result = await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    data = cls._dump_model(result)
                    data["_initialize"] = cls._dump_model(initialize_result)
                    return data
        except Exception as exc:
            if data is not None and cls.is_session_close_error(exc):
                return data
            raise

    @classmethod
    def runtime_transport_context(
            cls,
            *,
            server_url: str,
            transport_type: int,
            headers: dict,
            timeout_seconds: int,
    ):
        cls.ensure_supported_transport(transport_type)
        timeout = cls.runtime_timeout(timeout_seconds)
        return streamablehttp_client(
            server_url,
            headers=headers,
            timeout=timeout,
            sse_read_timeout=timeout,
            httpx_client_factory=cls.create_no_proxy_http_client,
        )

    @staticmethod
    def ensure_supported_transport(transport_type: int):
        if transport_type != AiMcpTransportTypeEnum.STREAMABLE_HTTP.value:
            raise ai_service_error("API自动化一期仅支持 Streamable HTTP MCP")

    @staticmethod
    def runtime_timeout(timeout_seconds: int):
        return timedelta(seconds=timeout_seconds or 60)

    @staticmethod
    def create_no_proxy_http_client(
            headers: dict[str, str] | None = None,
            timeout: httpx.Timeout | None = None,
            auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {
            "follow_redirects": True,
            "trust_env": False,
        }
        if timeout is not None:
            kwargs["timeout"] = timeout
        if headers is not None:
            kwargs["headers"] = headers
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(**kwargs)

    @classmethod
    def format_exception(cls, exc: BaseException) -> str:
        details = cls.flatten_exception_messages(exc)
        if not details:
            return str(exc)
        if len(details) == 1:
            return details[0]
        return "；".join(f"{index + 1}. {message}" for index, message in enumerate(details))

    @classmethod
    def flatten_exception_messages(cls, exc: BaseException) -> list[str]:
        children = getattr(exc, "exceptions", None)
        if children:
            messages = []
            for child in children:
                messages.extend(cls.flatten_exception_messages(child))
            return messages
        message = str(exc).strip() or exc.__class__.__name__
        return [f"{exc.__class__.__name__}: {message}"]

    @classmethod
    def is_session_close_error(cls, exc: BaseException) -> bool:
        messages = cls.flatten_exception_messages(exc)
        text = " ".join(messages).lower()
        return "taskgroup" in text or "cancel" in text or "closed" in text

    @classmethod
    async def _list_capabilities_from_session(cls, session: ClientSession) -> dict:
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
