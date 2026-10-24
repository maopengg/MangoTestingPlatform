# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.api.serializers.assistant_session import AiAssistantSessionSerializer
from src.apps.ai.models import AiAssistantSession
from src.apps.ai.services.assistant import AiAssistantService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0181,
    RESPONSE_MSG_0184,
)


class AiAssistantViews(ViewSet):
    model = AiAssistantSession
    serializer_class = AiAssistantSessionSerializer
    action_permission_map = {
        'status': 'index.home',
        'session': 'ai.task:detail',
        'sessions': 'ai.task:detail',
        'create_session': 'ai.task:create',
        'clear': 'ai.task:delete',
    }

    @action(methods=["get"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0001,
            AiAssistantService.builtin_status(request, preferred_server_id=request.query_params.get("mcp_server_id")),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def session(self, request: Request):
        session = AiAssistantService.get_or_create_session(request, session_id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantSessionSerializer(instance=session).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def sessions(self, request: Request):
        queryset = AiAssistantService.list_sessions(request)
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantSessionSerializer(instance=queryset, many=True).data,
                                    queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create_session(self, request: Request):
        session = AiAssistantService.create_session(
            request,
            page_context=request.data.get("page_context") or {},
            title=request.data.get("title") or "",
        )
        return ResponseData.success(RESPONSE_MSG_0184, AiAssistantSessionSerializer(instance=session).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def clear(self, request: Request):
        AiAssistantService.clear_session(request, request.data.get("session_id"))
        return ResponseData.success(RESPONSE_MSG_0181)
