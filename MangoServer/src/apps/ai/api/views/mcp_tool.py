# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.api.serializers.mcp_tool import AiMcpToolSerializer
from src.apps.ai.models import AiMcpTool
from src.apps.ai.services.core import McpService
from src.apps.ai.services.mcp_api_import import McpApiImportService
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MCP_API_API_INFO_BINDING_INVALID,
)
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    MCP_OPERATION_FAILED,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0168,
)


class AiMcpToolCRUD(ModelCRUD):
    model = AiMcpTool
    queryset = AiMcpTool.objects.all()
    serializer_class = AiMcpToolSerializer
    serializer = AiMcpToolSerializer
    page_permission_key = 'ai.mcp'
    not_matching_str = ModelCRUD.not_matching_str + ["server", "risk_level", "enabled", "require_confirm"]


class AiMcpToolViews(ViewSet):
    model = AiMcpTool
    serializer_class = AiMcpToolSerializer
    action_permission_map = {
        'status': 'ai.mcp:status',
        'call': 'ai.mcp:debug',
        'import_api_info': 'api.info:edit',
    }

    @action(methods=["put"], detail=False)
    @error_response("system")
    def status(self, request: Request):
        tool = AiMcpTool.objects.get(id=request.data.get("id"))
        for field in ("enabled", "require_confirm", "risk_level"):
            if field in request.data:
                setattr(tool, field, request.data.get(field))
        tool.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
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
            result = McpService.call_tool(tool.server, tool.name, request.data.get("arguments") or {},
                                          McpService.request_user_id(request))
        except Exception as exc:
            return ResponseData.fail(MCP_OPERATION_FAILED)
        return ResponseData.success(RESPONSE_MSG_0168, result)

    @action(methods=["post"], detail=False)
    @error_response("api")
    def import_api_info(self, request: Request):
        tool_ids = request.data.get("tool_ids") or []
        if request.data.get("tool_id"):
            tool_ids = [request.data.get("tool_id")]
        if not isinstance(tool_ids, list) or not tool_ids:
            raise AutoApiError(MCP_API_API_INFO_BINDING_INVALID)
        imported = McpApiImportService.import_tools(
            [int(tool_id) for tool_id in tool_ids],
            operator_id=request.user.get("id") if isinstance(request.user, dict) else None,
            project_product_id=request.data.get("project_product"),
            module_id=request.data.get("module"),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {"items": imported, "count": len(imported)})
