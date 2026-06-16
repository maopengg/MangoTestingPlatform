# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiMcpTool
from src.apps.ai.service.core import McpService
from src.apps.ai.views.mcp_server import AiMcpServerSerializer
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiMcpToolSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    category = serializers.SerializerMethodField()
    category_title = serializers.SerializerMethodField()

    class Meta:
        model = AiMcpTool
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("server")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["server"] = AiMcpServerSerializer(instance=instance.server).data if instance.server_id else None
        return data

    @staticmethod
    def get_category(instance):
        return McpService.tool_category(instance.name)["key"]

    @staticmethod
    def get_category_title(instance):
        return McpService.tool_category(instance.name)["title"]


class AiMcpToolCRUD(ModelCRUD):
    model = AiMcpTool
    queryset = AiMcpTool.objects.all()
    serializer_class = AiMcpToolSerializer
    serializer = AiMcpToolSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["server", "risk_level", "enabled", "require_confirm"]


class AiMcpToolViews(ViewSet):
    model = AiMcpTool
    serializer_class = AiMcpToolSerializer

    @action(methods=["put"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        tool = AiMcpTool.objects.get(id=request.data.get("id"))
        for field in ("enabled", "require_confirm", "risk_level"):
            if field in request.data:
                setattr(tool, field, request.data.get(field))
        tool.save()
        return ResponseData.success(RESPONSE_MSG_0082, AiMcpToolSerializer(instance=tool).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def call(self, request: Request):
        tool = AiMcpTool.objects.select_related("server").get(id=request.data.get("id"))
        if tool.tool_type != "tool":
            return ResponseData.fail(RESPONSE_MSG_0003, "只有 MCP tool 支持直接调用")
        if not tool.enabled:
            return ResponseData.fail(RESPONSE_MSG_0003, "该 MCP tool 已停用")
        try:
            result = McpService.call_tool(tool.server, tool.name, request.data.get("arguments") or {}, McpService.request_user_id(request))
        except Exception as exc:
            return ResponseData.fail(RESPONSE_MSG_0003, str(exc))
        return ResponseData.success(RESPONSE_MSG_0168, result)
