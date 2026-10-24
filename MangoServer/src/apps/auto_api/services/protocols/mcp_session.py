# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from contextlib import AsyncExitStack
from typing import Any

from mcp.client.session import ClientSession

from src.apps.ai.services.mcp_client import ExternalMcpClient
from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.exceptions import API_MCP_SESSION_CLOSED, AutoApiError
from src.common.logging import log


class McpSessionManager:
    """单次 API Case 执行内的 MCP Session 管理器。"""

    def __init__(self, trace_recorder=None):
        self.trace_recorder = trace_recorder
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="mango-mcp-session", daemon=True)
        self._thread.start()
        self._sessions: dict[str, dict] = {}
        self._closed = False

    def call_tool(
            self,
            *,
            server_url: str,
            transport_type: int,
            headers: dict | None,
            tool_name: str,
            arguments: dict | None,
            timeout_seconds: int,
            parent_step_id: int | None = None,
    ) -> dict:
        ExternalMcpClient.ensure_supported_transport(transport_type)
        headers = headers or {}
        session_key = self.session_key(server_url, transport_type, headers)
        initialize_result = None
        if session_key not in self._sessions:
            connect_step = self._start_trace_step(
                ApiCaseTraceStepType.MCP_CONNECT,
                "初始化 MCP Session",
                {
                    "server_url": server_url,
                    "transport_type": transport_type,
                    "headers_fingerprint": self.headers_fingerprint(headers),
                    "reused": False,
                },
                parent_step_id,
            )
            try:
                initialize_result = self._run(self._ensure_session(
                    session_key=session_key,
                    server_url=server_url,
                    transport_type=transport_type,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
                ))
                self._finish_trace_step(connect_step, {
                    "reused": False,
                    "protocol_version": (initialize_result or {}).get("protocolVersion"),
                })
            except Exception as error:
                self._fail_trace_step(connect_step, str(error))
                raise
        else:
            initialize_result = self._sessions[session_key].get("initialize")
            reuse_step = self._start_trace_step(
                ApiCaseTraceStepType.MCP_CONNECT,
                "复用 MCP Session",
                {
                    "server_url": server_url,
                    "transport_type": transport_type,
                    "headers_fingerprint": self.headers_fingerprint(headers),
                    "reused": True,
                    "protocol_version": (initialize_result or {}).get("protocolVersion"),
                },
                parent_step_id,
            )
            self._finish_trace_step(reuse_step, {"reused": True})

        call_step = self._start_trace_step(
            ApiCaseTraceStepType.MCP_TOOL_CALL,
            f"MCP Tool 调用：{tool_name}",
            {
                "tool_name": tool_name,
                "arguments_keys": list((arguments or {}).keys()),
                "timeout_seconds": timeout_seconds,
            },
            parent_step_id,
        )
        try:
            result = self._run(self._call_tool(session_key, tool_name, arguments or {}))
            result["_initialize"] = initialize_result or {}
            self._finish_trace_step(call_step, self.tool_call_summary(result))
            return result
        except Exception as error:
            self._fail_trace_step(call_step, str(error))
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        close_step = self._start_trace_step(
            ApiCaseTraceStepType.MCP_CLOSE,
            "关闭 MCP Session",
            {"session_count": len(self._sessions)},
            None,
        )
        try:
            self._run(self._close_all())
            self._finish_trace_step(close_step)
        except Exception as error:
            self._fail_trace_step(close_step, str(error))
            log.api.error(f'MCP Session关闭失败：{error}')
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=3)
        except Exception as error:
            log.api.error(f'MCP Session事件循环停止失败：{error}')

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _ensure_session(
            self,
            *,
            session_key: str,
            server_url: str,
            transport_type: int,
            headers: dict,
            timeout_seconds: int,
    ) -> dict:
        if session_key in self._sessions:
            return self._sessions[session_key].get("initialize") or {}
        timeout = ExternalMcpClient.runtime_timeout(timeout_seconds)
        stack = AsyncExitStack()
        read_stream, write_stream, _ = await stack.enter_async_context(ExternalMcpClient.runtime_transport_context(
            server_url=server_url,
            transport_type=transport_type,
            headers=headers,
            timeout_seconds=timeout_seconds,
        ))
        session = await stack.enter_async_context(ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timeout,
        ))
        initialize_result = await session.initialize()
        initialize_data = ExternalMcpClient._dump_model(initialize_result)
        self._sessions[session_key] = {
            "stack": stack,
            "session": session,
            "initialize": initialize_data,
        }
        return initialize_data

    async def _call_tool(self, session_key: str, tool_name: str, arguments: dict) -> dict:
        session_data = self._sessions.get(session_key)
        if not session_data:
            raise AutoApiError(API_MCP_SESSION_CLOSED)
        result = await session_data["session"].call_tool(tool_name, arguments=arguments)
        return ExternalMcpClient._dump_model(result)

    async def _close_all(self):
        sessions = list(self._sessions.values())
        self._sessions = {}
        for session_data in reversed(sessions):
            try:
                await session_data["stack"].aclose()
            except Exception as error:
                log.api.error(f'MCP Session关闭单个连接失败：{error}')

    @staticmethod
    def session_key(server_url: str, transport_type: int, headers: dict) -> str:
        payload = json.dumps(
            {
                "server_url": server_url,
                "transport_type": transport_type,
                "headers": headers or {},
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def headers_fingerprint(headers: dict) -> str:
        payload = json.dumps(headers or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def tool_call_summary(result: dict) -> dict:
        content = result.get("content") if isinstance(result, dict) else None
        return {
            "is_error": bool(result.get("isError")) if isinstance(result, dict) else None,
            "content_count": len(content) if isinstance(content, list) else 0,
            "has_structured_content": isinstance(result, dict) and result.get("structuredContent") is not None,
            "has_notifications": bool(result.get("notifications")) if isinstance(result, dict) else False,
            "has_task": bool(result.get("task")) if isinstance(result, dict) else False,
        }

    def _start_trace_step(self, step_type: str, step_name: str, input_summary: Any, parent_step_id: int | None):
        if not self.trace_recorder:
            return None
        return self.trace_recorder.start_step(
            step_type,
            step_name,
            input_summary,
            parent_step_id=parent_step_id,
        )

    def _finish_trace_step(self, step, output_summary: Any = None):
        if self.trace_recorder:
            self.trace_recorder.finish_step(step, output_summary)

    def _fail_trace_step(self, step, error_message: str | None):
        if self.trace_recorder:
            self.trace_recorder.fail_step(step, error_message)
