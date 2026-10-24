# -*- coding: utf-8 -*-
import json

from django.http import StreamingHttpResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.api.serializers.assistant_message import AiAssistantMessageSerializer
from src.apps.ai.exceptions import AiError
from src.apps.ai.models import AiAssistantMessage
from src.apps.ai.services.assistant import AiAssistantService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    AI_OPERATION_FAILED,
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0177,
    RESPONSE_MSG_0179,
    RESPONSE_MSG_0180,
    RESPONSE_MSG_0182,
)


class AiAssistantMessageViews(ViewSet):
    model = AiAssistantMessage
    serializer_class = AiAssistantMessageSerializer
    action_permission_map = {
        'messages': 'ai.task:detail',
        'message': 'ai.task:create',
        'message_stream': 'ai.task:create',
        'tool_confirm': 'ai.task:debug',
    }

    @action(methods=["get"], detail=False)
    @error_response("system")
    def messages(self, request: Request):
        session = AiAssistantService.get_or_create_session(request, session_id=request.query_params.get("session_id"))
        queryset = AiAssistantService.messages(session)
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantMessageSerializer(instance=queryset, many=True).data,
                                    queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def message(self, request: Request):
        content = (request.data.get("content") or "").strip()
        if not content:
            return ResponseData.fail(RESPONSE_MSG_0182)
        try:
            data = AiAssistantService.chat(
                request,
                content,
                session_id=request.data.get("session_id"),
                page_context=request.data.get("page_context") or {},
                mcp_server_id=request.data.get("mcp_server_id"),
            )
        except AiError as exc:
            return ResponseData.fail(AI_OPERATION_FAILED)
        if not data.get("mcp_online"):
            return ResponseData.fail(RESPONSE_MSG_0179, data)
        return ResponseData.success(RESPONSE_MSG_0180, data)

    @action(methods=["post"], detail=False)
    def message_stream(self, request: Request):
        content = (request.data.get("content") or "").strip()

        def event_stream():
            if not content:
                yield f"event: error\ndata: {json.dumps({'message': RESPONSE_MSG_0182[1]}, ensure_ascii=False)}\n\n"
                return
            try:
                for event in AiAssistantService.stream_chat(
                        request,
                        content,
                        session_id=request.data.get("session_id"),
                        page_context=request.data.get("page_context") or {},
                        mcp_server_id=request.data.get("mcp_server_id"),
                ):
                    yield (
                        f"event: {event.get('event', 'message')}\n"
                        f"data: {json.dumps(event.get('data') or {}, ensure_ascii=False)}\n\n"
                    )
            except AiError as exc:
                yield f"event: error\ndata: {json.dumps({'message': RESPONSE_MSG_0177[1].format(str(exc))}, ensure_ascii=False)}\n\n"
            except Exception as exc:
                message = str(exc).strip() or exc.__class__.__name__
                if message == "(0, '')":
                    message = "AI流式响应异常：连接提前结束或返回了空错误，请重试；如果反复出现，后端会自动降级为非流式响应。"
                yield f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(methods=["post"], detail=False)
    @error_response("system")
    def tool_confirm(self, request: Request):
        try:
            data = AiAssistantService.confirm_tool(request, request.data.get("message_id"))
        except AiError as exc:
            return ResponseData.fail(AI_OPERATION_FAILED)
        if not data.get("mcp_online"):
            return ResponseData.fail(RESPONSE_MSG_0179, data)
        return ResponseData.success(RESPONSE_MSG_0180, data)
