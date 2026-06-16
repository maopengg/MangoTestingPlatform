# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiMcpServer
from src.apps.ai.service.core import McpService, mask_sensitive
from src.apps.user.views.user import UserSerializers
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiMcpServerSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_test_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    is_builtin = serializers.SerializerMethodField()
    is_builtin_local = serializers.SerializerMethodField()
    is_builtin_manual = serializers.SerializerMethodField()
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = AiMcpServer
        fields = "__all__"

    def validate_prompt(self, value):
        if not str(value or "").strip():
            raise serializers.ValidationError("MCP使用提示词不能为空")
        return str(value).strip()

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("create_user", "update_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["auth_config"] = mask_sensitive(data.get("auth_config") or {})
        data["create_user"] = UserSerializers(instance=instance.create_user).data if instance.create_user_id else None
        data["update_user"] = UserSerializers(instance=instance.update_user).data if instance.update_user_id else None
        return data

    @staticmethod
    def get_is_builtin(instance):
        return bool((instance.auth_config or {}).get("builtin"))

    @staticmethod
    def get_is_builtin_local(instance):
        return bool((instance.auth_config or {}).get("builtin_local"))

    @staticmethod
    def get_is_builtin_manual(instance):
        return bool((instance.auth_config or {}).get("builtin_manual"))

    @staticmethod
    def get_is_connected(instance):
        return bool(instance.last_test_time and not instance.last_error)


class AiMcpServerCRUD(ModelCRUD):
    model = AiMcpServer
    queryset = AiMcpServer.objects.all()
    serializer_class = AiMcpServerSerializer
    serializer = AiMcpServerSerializer

    @error_response("system")
    def get(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = self.serializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer(instance=queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        data["create_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        data = dict(request.data)
        auth_config = data.get("auth_config")
        if isinstance(auth_config, dict) and data.get("id"):
            old_config = AiMcpServer.objects.filter(id=data.get("id")).values_list("auth_config", flat=True).first() or {}
            merged_config = dict(old_config)
            for key, value in auth_config.items():
                if value == "***":
                    continue
                merged_config[key] = value
            data["auth_config"] = merged_config
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        return super().put(data)


class AiMcpServerViews(ViewSet):
    model = AiMcpServer
    serializer_class = AiMcpServerSerializer

    @action(methods=["post"], detail=False)
    @error_response("system")
    def test(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0035, McpService.test_server(server, McpService.request_user_id(request)))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def refresh_status(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = AiMcpServerSerializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0035, AiMcpServerSerializer(instance=queryset, many=True).data, queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def builtin(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0082, AiMcpServerSerializer(instance=McpService.set_builtin(server, bool(request.data.get("is_builtin")))).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def sync_tools(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        user_id = McpService.request_user_id(request)
        result = McpService.test_server(server, user_id)
        if not result.get("ok"):
            return ResponseData.fail(RESPONSE_MSG_0003, result)
        return ResponseData.success(RESPONSE_MSG_0035, McpService.sync_tools(server, user_id))
