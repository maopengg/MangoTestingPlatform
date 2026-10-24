# -*- coding: utf-8 -*-
from __future__ import annotations

from django.db import transaction

from src.apps.ai.enums import AiMcpUseTypeEnum
from src.apps.ai.models import AiMcpTool
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MCP_API_SERVICE_INVALID,
    MCP_API_TYPE_INVALID,
    MCP_API_API_INFO_TYPE_NOT_ALLOWED,
    MCP_API_PROJECT_PRODUCT_MODULE_CONFIG_REQUIRED,
)
from src.apps.auto_api.services.api_info.mcp_import import ApiInfoMcpImportService


class McpApiImportService:
    @classmethod
    @transaction.atomic
    def import_tools(
            cls,
            tool_ids: list[int],
            *,
            operator_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
    ) -> list[dict]:
        imported = []
        tools = (
            AiMcpTool.objects
            .select_related("server")
            .select_for_update()
            .filter(id__in=tool_ids)
            .order_by("id")
        )
        for tool in tools:
            imported.append(cls.import_tool(
                tool,
                operator_id=operator_id,
                project_product_id=project_product_id,
                module_id=module_id,
            ))
        return imported

    @classmethod
    def import_tool(
            cls,
            tool: AiMcpTool,
            *,
            operator_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
    ) -> dict:
        if tool.tool_type != "tool":
            raise AutoApiError(MCP_API_TYPE_INVALID, value=(tool.tool_type,))
        if not tool.enabled:
            raise AutoApiError(MCP_API_SERVICE_INVALID, value=(tool.name,))
        if tool.type not in {AiMcpUseTypeEnum.API_AUTOMATION.value, AiMcpUseTypeEnum.COMMON.value}:
            raise AutoApiError(MCP_API_API_INFO_TYPE_NOT_ALLOWED, value=(tool.name,))

        effective_project_product_id = tool.project_product_id or tool.server.project_product_id or project_product_id
        effective_module_id = tool.module_id or tool.server.module_id or module_id
        if not effective_project_product_id or not effective_module_id:
            raise AutoApiError(MCP_API_PROJECT_PRODUCT_MODULE_CONFIG_REQUIRED, value=(tool.name,))

        return ApiInfoMcpImportService.upsert(
            tool_id=tool.id,
            tool_name=tool.name,
            tool_title=tool.title,
            server_url=tool.server.server_url,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            project_product_id=effective_project_product_id,
            module_id=effective_module_id,
            operator_id=operator_id,
        )
