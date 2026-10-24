# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.api.serializers.mcp_server_mutation import AiMcpServerSerializer
from src.apps.ai.models import AiMcpServer
from src.apps.ai.services.core import McpService
from src.apps.ai.services.mcp_server import AiMcpServerMutationService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0035,
    RESPONSE_MSG_0082,
)


class AiMcpServerCRUD(ModelCRUD):
    model = AiMcpServer
    queryset = AiMcpServer.objects.all()
    serializer_class = AiMcpServerSerializer
    serializer = AiMcpServerSerializer
    page_permission_key = 'ai.mcp'

    @error_response("system")
    def get(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = self.serializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, self.serializer(instance=queryset, many=True).data,
                                    queryset.count())

    @error_response("system")
    def post(self, request: Request):
        result = AiMcpServerMutationService.create(
            dict(request.data),
            McpService.request_user_id(request),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def put(self, request: Request):
        result = AiMcpServerMutationService.update(
            request.data.get("id"),
            dict(request.data),
            McpService.request_user_id(request),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            self.serializer(instance=result.instance).data,
        )


class AiMcpServerViews(ViewSet):
    model = AiMcpServer
    serializer_class = AiMcpServerSerializer
    action_permission_map = {
        'test': 'ai.mcp:debug',
        'refresh_status': 'ai.mcp:status',
        'builtin': 'ai.mcp:status',
        'sync_tools': 'ai.mcp:status',
    }

    @action(methods=["post"], detail=False)
    @error_response("system")
    def test(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0035,
                                    McpService.test_server(server, McpService.request_user_id(request)))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def refresh_status(self, request: Request):
        McpService.ensure_builtin_server(request)
        queryset = AiMcpServerSerializer.setup_eager_loading(AiMcpServer.objects.all())
        McpService.refresh_statuses(queryset, McpService.request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0035, AiMcpServerSerializer(instance=queryset, many=True).data,
                                    queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def builtin(self, request: Request):
        server = AiMcpServer.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0082, AiMcpServerSerializer(
            instance=McpService.set_builtin(server, bool(request.data.get("is_builtin")))).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def sync_tools(self, request: Request):
        user_id = McpService.request_user_id(request)
        result = AiMcpServerMutationService.sync_tools(
            request.data.get("id"),
            user_id,
            test_env=request.data.get("test_env"),
        )
        if result.sync_error:
            return ResponseData.fail(RESPONSE_MSG_0003, {"error": result.sync_error})
        if not result.test_result.get("ok"):
            return ResponseData.fail(RESPONSE_MSG_0003, result.test_result)
        return ResponseData.success(
            RESPONSE_MSG_0035,
            result.sync_result,
        )
