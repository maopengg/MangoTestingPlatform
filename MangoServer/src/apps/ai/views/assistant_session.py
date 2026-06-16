# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiAssistantSession
from src.apps.ai.service.assistant import AiAssistantService
from src.apps.user.views.user import UserSerializers
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiAssistantSessionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAssistantSession
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("create_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["create_user"] = UserSerializers(instance=instance.create_user).data if instance.create_user_id else None
        return data


class AiAssistantViews(ViewSet):
    model = AiAssistantSession
    serializer_class = AiAssistantSessionSerializer

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
        return ResponseData.success(RESPONSE_MSG_0001, AiAssistantSessionSerializer(instance=queryset, many=True).data, queryset.count())

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
