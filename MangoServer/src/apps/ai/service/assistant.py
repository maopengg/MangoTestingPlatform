# -*- coding: utf-8 -*-
import json

from django.db.models import QuerySet

from src.apps.ai.models import AiAssistantMessage, AiAssistantSession, AiMcpTool
from src.apps.ai.service.core import McpService, mask_sensitive
from src.apps.system.service.ai.client import AiService
from src.common.enums.ai_enum import AiMcpToolRiskLevelEnum


class AiAssistantService:
    HISTORY_LIMIT = 16
    SESSION_LIMIT = 10
    TOOL_LIMIT = 64

    SYSTEM_PROMPT = (
        "你是芒果测试平台的 AI 助手。你可以直接回答平台使用、测试设计和当前页面相关问题。"
        "如果当前选择的 MCP 在线且提供可用工具，可以优先结合 MCP 工具结果；如果 MCP 不在线，不要假装已经查询平台数据。"
        "如果需要创建、修改、删除、执行或绑定平台数据，必须先返回工具调用，由平台进行二次确认，"
        "不要声称已经完成未执行的写操作。"
    )

    @classmethod
    def builtin_status(cls, request, preferred_server_id: int | None = None) -> dict:
        ai_status = cls.ai_status()
        server, statuses = McpService.select_online_server(request, preferred_server_id=preferred_server_id)
        if preferred_server_id:
            preferred_id = int(preferred_server_id)
            preferred_status = next((item for item in statuses if item.get("server_id") == preferred_id), None)
            if preferred_status and preferred_status.get("is_connected"):
                server = next((item for item in McpService.mcp_candidates(request) if item.id == preferred_id), None)
            else:
                server = None
        return {
            "ai_available": ai_status["available"],
            "ai_message": ai_status["message"],
            "ai_model": ai_status.get("model") or "",
            "server_id": server.id if server else None,
            "server_name": server.name if server else "",
            "server_url": server.server_url if server else "",
            "server_prompt": server.prompt if server else "",
            "is_connected": bool(server),
            "last_error": "" if server else "没有可用的 MCP 连接",
            "candidates": statuses,
        }

    @classmethod
    def ai_status(cls) -> dict:
        try:
            data = AiService.test_config()
        except Exception as error:
            return {
                "available": False,
                "message": str(error),
            }
        return {
            "available": True,
            "message": "AI配置可用",
            "model": data.get("model"),
        }

    @classmethod
    def get_or_create_session(cls, request, session_id=None, page_context: dict | None = None) -> AiAssistantSession:
        user_id = McpService.request_user_id(request)
        if session_id:
            return AiAssistantSession.objects.get(id=session_id, create_user_id=user_id)
        session = (
            AiAssistantSession.objects.filter(create_user_id=user_id, status="active")
            .order_by("-id")
            .first()
        )
        if session:
            if page_context:
                cls.update_page_context(session, page_context)
            return session
        session = AiAssistantSession.objects.create(
            title="Mango AI 助手",
            create_user_id=user_id,
            current_page=cls.page_context_label(page_context or {}),
            page_context=page_context or {},
        )
        cls.prune_user_sessions(user_id)
        return session

    @classmethod
    def list_sessions(cls, request) -> QuerySet:
        cls.prune_user_sessions(McpService.request_user_id(request))
        return AiAssistantSession.objects.filter(
            create_user_id=McpService.request_user_id(request),
            status="active",
        ).order_by("-update_time", "-id")[: cls.SESSION_LIMIT]

    @classmethod
    def create_session(cls, request, page_context: dict | None = None, title: str = "") -> AiAssistantSession:
        user_id = McpService.request_user_id(request)
        session = AiAssistantSession.objects.create(
            title=(title or "新会话")[:128],
            create_user_id=user_id,
            current_page=cls.page_context_label(page_context or {}),
            page_context=page_context or {},
        )
        cls.prune_user_sessions(user_id)
        return session

    @classmethod
    def prune_user_sessions(cls, user_id: int | None):
        if not user_id:
            return
        keep_ids = list(
            AiAssistantSession.objects.filter(create_user_id=user_id, status="active")
            .order_by("-update_time", "-id")
            .values_list("id", flat=True)[: cls.SESSION_LIMIT]
        )
        AiAssistantSession.objects.filter(create_user_id=user_id, status="active").exclude(id__in=keep_ids).delete()

    @staticmethod
    def page_context_label(page_context: dict) -> str:
        return str(page_context.get("title") or page_context.get("name") or page_context.get("route") or "")[:512]

    @classmethod
    def update_page_context(cls, session: AiAssistantSession, page_context: dict):
        current_page = cls.page_context_label(page_context) or session.current_page
        session.current_page = current_page
        session.page_context = page_context
        session.save(update_fields=["current_page", "page_context", "update_time"])

    @classmethod
    def messages(cls, session: AiAssistantSession) -> QuerySet:
        return AiAssistantMessage.objects.filter(session=session)

    @classmethod
    def clear_session(cls, request, session_id: int):
        session = cls.get_or_create_session(request, session_id=session_id)
        session.status = "cleared"
        session.save(update_fields=["status", "update_time"])
        return session

    @classmethod
    def chat(cls, request, content: str, session_id=None, page_context: dict | None = None, mcp_server_id=None) -> dict:
        status = cls.builtin_status(request, preferred_server_id=mcp_server_id)
        if not status["ai_available"]:
            return {"ai_available": False, "status": status}

        session = cls.get_or_create_session(request, session_id=session_id, page_context=page_context or {})
        user_message = AiAssistantMessage.objects.create(
            session=session,
            role="user",
            content=content,
            metadata={"page_context": page_context or {}},
        )
        if session.title in ("新会话", "Mango AI 助手"):
            session.title = content[:32]
            session.save(update_fields=["title", "update_time"])
        messages = cls._build_messages(session, content, status)
        tools = cls._build_tools(status["server_id"], content)
        response = (
            AiService.chat_with_tools(messages=messages, tools=tools, tool_choice="auto", max_tokens=1600)
            if tools
            else AiService.chat(messages=messages, max_tokens=1600)
        )
        first_message = cls._first_message(response)
        tool_calls = first_message.get("tool_calls") or []

        if not tool_calls:
            assistant_content = cls._content(first_message) or "我暂时没有得到有效回答。"
            assistant_message = AiAssistantMessage.objects.create(
                session=session,
                role="assistant",
                content=assistant_content,
                metadata={"ai_response": mask_sensitive(response), "reply_to": user_message.id},
            )
            return cls._payload(session, assistant_message, status)

        tool_call = tool_calls[0]
        tool_name, arguments = cls._tool_call_parts(tool_call)
        tool = AiMcpTool.objects.filter(server_id=status["server_id"], name=tool_name, tool_type="tool", enabled=True).first()
        if not tool:
            assistant_message = AiAssistantMessage.objects.create(
                session=session,
                role="assistant",
                content=f"当前 MCP 中未找到可用工具：{tool_name}",
                metadata={"ai_response": mask_sensitive(response), "reply_to": user_message.id},
            )
            return cls._payload(session, assistant_message, status)

        confirm_required = tool.require_confirm or tool.write_operation or tool.risk_level in (
            AiMcpToolRiskLevelEnum.WRITE.value,
            AiMcpToolRiskLevelEnum.EXECUTE.value,
            AiMcpToolRiskLevelEnum.DELETE.value,
        )
        if confirm_required:
            assistant_message = AiAssistantMessage.objects.create(
                session=session,
                role="assistant",
                content=f"需要确认后才能调用 MCP 工具：{tool_name}",
                tool_name=tool_name,
                tool_arguments=arguments,
                metadata={
                    "need_confirm": True,
                    "risk_level": tool.risk_level,
                    "tool_title": tool.title or tool.name,
                    "tool_description": tool.description or "",
                    "ai_response": mask_sensitive(response),
                    "reply_to": user_message.id,
                },
            )
            return cls._payload(session, assistant_message, status, need_confirm=True)

        result = McpService.call_tool(tool.server, tool.name, arguments, McpService.request_user_id(request))
        tool_message = AiAssistantMessage.objects.create(
            session=session,
            role="tool",
            content=f"MCP 工具 {tool.name} 调用完成",
            tool_name=tool.name,
            tool_arguments=mask_sensitive(arguments),
            tool_result=mask_sensitive(result),
            metadata={"reply_to": user_message.id},
        )
        assistant_content = cls._summarize_tool_result(session, content, tool.name, result)
        assistant_message = AiAssistantMessage.objects.create(
            session=session,
            role="assistant",
            content=assistant_content,
            metadata={"tool_message_id": tool_message.id, "reply_to": user_message.id},
        )
        return cls._payload(session, assistant_message, status)

    @classmethod
    def stream_chat(cls, request, content: str, session_id=None, page_context: dict | None = None, mcp_server_id=None):
        status = cls.builtin_status(request, preferred_server_id=mcp_server_id)
        if not status["ai_available"]:
            yield {"event": "error", "data": {"message": status.get("ai_message") or "AI助手暂不可用", "status": status}}
            return

        session = cls.get_or_create_session(request, session_id=session_id, page_context=page_context or {})
        user_message = AiAssistantMessage.objects.create(
            session=session,
            role="user",
            content=content,
            metadata={"page_context": page_context or {}},
        )
        if session.title in ("新会话", "Mango AI 助手"):
            session.title = content[:32]
            session.save(update_fields=["title", "update_time"])

        yield {"event": "session", "data": {"session_id": session.id, "title": session.title}}

        messages = cls._build_messages(session, content, status)
        tools = cls._build_tools(status["server_id"], content)
        assistant_content = ""
        tool_calls: dict[int, dict] = {}

        for chunk in AiService.stream_chat(
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            max_tokens=1600,
        ):
            choice = (chunk.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            if delta.get("content"):
                assistant_content += delta["content"]
                yield {"event": "delta", "data": {"content": delta["content"]}}
            for tool_call in delta.get("tool_calls") or []:
                index = tool_call.get("index", 0)
                target = tool_calls.setdefault(index, {"function": {"name": "", "arguments": ""}})
                function = tool_call.get("function") or {}
                if function.get("name"):
                    target["function"]["name"] += function.get("name") or ""
                if function.get("arguments"):
                    target["function"]["arguments"] += function.get("arguments") or ""

        if assistant_content:
            assistant_message = AiAssistantMessage.objects.create(
                session=session,
                role="assistant",
                content=assistant_content,
                metadata={"reply_to": user_message.id, "stream": True},
            )
            yield {"event": "message", "data": cls._payload(session, assistant_message, status)["message"]}
            yield {"event": "done", "data": {"session_id": session.id}}
            return

        if tool_calls:
            tool_name, arguments = cls._tool_call_parts(next(iter(tool_calls.values())))
            tool = AiMcpTool.objects.filter(server_id=status["server_id"], name=tool_name, tool_type="tool", enabled=True).first()
            if not tool:
                assistant_message = AiAssistantMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=f"当前 MCP 中未找到可用工具：{tool_name}",
                    metadata={"reply_to": user_message.id, "stream": True},
                )
                yield {"event": "message", "data": cls._payload(session, assistant_message, status)["message"]}
                yield {"event": "done", "data": {"session_id": session.id}}
                return
            confirm_required = tool.require_confirm or tool.write_operation or tool.risk_level in (
                AiMcpToolRiskLevelEnum.WRITE.value,
                AiMcpToolRiskLevelEnum.EXECUTE.value,
                AiMcpToolRiskLevelEnum.DELETE.value,
            )
            if confirm_required:
                assistant_message = AiAssistantMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=f"需要确认后才能调用 MCP 工具：{tool_name}",
                    tool_name=tool_name,
                    tool_arguments=arguments,
                    metadata={
                        "need_confirm": True,
                        "risk_level": tool.risk_level,
                        "tool_title": tool.title or tool.name,
                        "tool_description": tool.description or "",
                        "reply_to": user_message.id,
                        "stream": True,
                    },
                )
                yield {"event": "message", "data": cls._payload(session, assistant_message, status, need_confirm=True)["message"]}
                yield {"event": "done", "data": {"session_id": session.id}}
                return
            result = McpService.call_tool(tool.server, tool.name, arguments, McpService.request_user_id(request))
            AiAssistantMessage.objects.create(
                session=session,
                role="tool",
                content=f"MCP 工具 {tool.name} 调用完成",
                tool_name=tool.name,
                tool_arguments=mask_sensitive(arguments),
                tool_result=mask_sensitive(result),
                metadata={"reply_to": user_message.id, "stream": True},
            )
            assistant_content = cls._summarize_tool_result(session, content, tool.name, result)
            assistant_message = AiAssistantMessage.objects.create(
                session=session,
                role="assistant",
                content=assistant_content,
                metadata={"reply_to": user_message.id, "stream": True},
            )
            yield {"event": "message", "data": cls._payload(session, assistant_message, status)["message"]}
            yield {"event": "done", "data": {"session_id": session.id}}
            return

        assistant_message = AiAssistantMessage.objects.create(
            session=session,
            role="assistant",
            content="我暂时没有得到有效回答。",
            metadata={"reply_to": user_message.id, "stream": True},
        )
        yield {"event": "message", "data": cls._payload(session, assistant_message, status)["message"]}
        yield {"event": "done", "data": {"session_id": session.id}}

    @classmethod
    def confirm_tool(cls, request, message_id: int) -> dict:
        status = cls.builtin_status(request)
        if not status["is_connected"]:
            return {"mcp_online": False, "status": status}
        message = AiAssistantMessage.objects.select_related("session").get(
            id=message_id,
            session__create_user_id=McpService.request_user_id(request),
        )
        tool = AiMcpTool.objects.select_related("server").get(
            server_id=status["server_id"],
            name=message.tool_name,
            tool_type="tool",
            enabled=True,
        )
        result = McpService.call_tool(tool.server, tool.name, message.tool_arguments or {}, McpService.request_user_id(request))
        message.tool_result = mask_sensitive(result)
        message.metadata = {**(message.metadata or {}), "confirmed": True, "need_confirm": False}
        message.save(update_fields=["tool_result", "metadata", "update_time"])
        content = cls._summarize_tool_result(message.session, message.content or "", tool.name, result)
        assistant_message = AiAssistantMessage.objects.create(
            session=message.session,
            role="assistant",
            content=content,
            metadata={"confirmed_tool_message_id": message.id},
        )
        return cls._payload(message.session, assistant_message, status)

    @classmethod
    def _build_messages(cls, session: AiAssistantSession, content: str, status: dict | None = None) -> list[dict]:
        history = list(AiAssistantMessage.objects.filter(session=session).order_by("-id")[: cls.HISTORY_LIMIT])
        history.reverse()
        messages = [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "system", "content": f"当前页面上下文：{json.dumps(session.page_context or {}, ensure_ascii=False)[:2000]}"},
        ]
        if status and status.get("server_prompt"):
            messages.append(
                {
                    "role": "system",
                    "content": f"当前 MCP 服务用途说明（{status.get('server_name') or status.get('server_id')}）：{status.get('server_prompt')[:3000]}",
                }
            )
        for item in history:
            if item.role in ("user", "assistant") and item.content:
                messages.append({"role": item.role, "content": item.content[:3000]})
        if not history or history[-1].content != content:
            messages.append({"role": "user", "content": content})
        return messages

    @classmethod
    def _build_tools(cls, server_id: int | None, content: str = "") -> list[dict]:
        if not server_id:
            return []
        categories = McpService.assistant_tool_categories(content)
        raw_tools = AiMcpTool.objects.filter(server_id=server_id, tool_type="tool", enabled=True).order_by("id")
        tools = [
            tool
            for tool in raw_tools
            if McpService.tool_category(tool.name)["key"] in categories
        ][: cls.TOOL_LIMIT]
        if not tools:
            tools = [tool for tool in raw_tools if not tool.write_operation][: min(cls.TOOL_LIMIT, 12)]
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": (tool.description or tool.title or tool.name)[:1000],
                    "parameters": tool.input_schema or {"type": "object", "properties": {}},
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _first_message(response: dict) -> dict:
        choices = response.get("choices") or []
        if not choices:
            return {}
        return choices[0].get("message") or {}

    @staticmethod
    def _content(message: dict) -> str:
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(item.get("text") or item) for item in content)
        return ""

    @staticmethod
    def _tool_call_parts(tool_call: dict) -> tuple[str, dict]:
        function = tool_call.get("function") or {}
        name = function.get("name") or tool_call.get("name") or ""
        raw_arguments = function.get("arguments") or tool_call.get("arguments") or "{}"
        if isinstance(raw_arguments, dict):
            return name, raw_arguments
        try:
            return name, json.loads(raw_arguments or "{}")
        except json.JSONDecodeError:
            return name, {"raw_arguments": raw_arguments}

    @classmethod
    def _summarize_tool_result(cls, session: AiAssistantSession, user_content: str, tool_name: str, result: dict) -> str:
        response = AiService.chat(
            messages=[
                {"role": "system", "content": cls.SYSTEM_PROMPT},
                {"role": "user", "content": user_content[:3000]},
                {
                    "role": "user",
                    "content": f"MCP 工具 {tool_name} 返回：{json.dumps(mask_sensitive(result), ensure_ascii=False)[:6000]}",
                },
            ],
            max_tokens=1200,
        )
        content = cls._content(cls._first_message(response))
        return content or "MCP 工具已调用完成，但 AI 未返回有效总结。"

    @staticmethod
    def _payload(session: AiAssistantSession, message: AiAssistantMessage, status: dict, need_confirm: bool = False) -> dict:
        return {
            "mcp_online": True,
            "status": status,
            "session_id": session.id,
            "message": {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "tool_name": message.tool_name,
                "tool_arguments": mask_sensitive(message.tool_arguments),
                "tool_result": mask_sensitive(message.tool_result),
                "metadata": mask_sensitive(message.metadata),
                "need_confirm": need_confirm or bool((message.metadata or {}).get("need_confirm")),
                "create_time": message.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
