from urllib.parse import urlparse

from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.models import ApiInfo, ApiInfoMcpBinding, ApiInfoMcpConfig
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService


class ApiInfoMcpImportService:
    """Own creation and refresh of API assets backed by an MCP tool."""

    @staticmethod
    def endpoint_path(server_url: str | None) -> str:
        parsed = urlparse((server_url or "").strip())
        if parsed.scheme or parsed.netloc:
            return parsed.path or "/"
        return parsed.path or server_url or "/"

    @staticmethod
    def disable_for_tool(tool_id: int) -> bool:
        binding = (
            ApiInfoMcpBinding.objects.select_related("api_info")
            .filter(mcp_tool_id=tool_id)
            .first()
        )
        if not binding or binding.api_info.status == StatusEnum.FAIL.value:
            return False
        binding.api_info.status = StatusEnum.FAIL.value
        binding.api_info.save(update_fields=["status", "update_time"])
        return True

    @classmethod
    @transaction.atomic
    def upsert(
            cls,
            *,
            tool_id: int,
            tool_name: str,
            tool_title: str | None,
            server_url: str | None,
            input_schema: dict | None,
            output_schema: dict | None,
            project_product_id: int,
            module_id: int,
            operator_id: int | None,
    ) -> dict:
        binding = (
            ApiInfoMcpBinding.objects.select_related("api_info")
            .filter(mcp_tool_id=tool_id)
            .first()
        )
        normalized_url = cls.endpoint_path(server_url)
        if binding:
            api_info = binding.api_info
            if api_info.url != normalized_url:
                api_info.url = normalized_url
                api_info.update_user_id = operator_id
                api_info.save(update_fields=["url", "update_user_id", "update_time"])
            ApiInfoMcpConfig.objects.update_or_create(
                api_info=api_info,
                defaults={
                    "mcp_tool_id": tool_id,
                    "mcp_config": None,
                    "input_schema": input_schema,
                    "output_schema": output_schema,
                    "schema_hash": ApiInfoRuntimeService.mcp_schema_hash(
                        input_schema,
                        output_schema,
                    ),
                },
            )
            return {
                "tool_id": tool_id,
                "tool_name": tool_name,
                "api_info_id": binding.api_info_id,
                "created": False,
            }

        api_info = ApiInfo.objects.create(
            project_product_id=project_product_id,
            module_id=module_id,
            name=tool_title or tool_name,
            url=normalized_url,
            protocol_type=ApiProtocolTypeEnum.MCP.value,
            status=1,
            update_user_id=operator_id,
        )
        ApiInfoMcpBinding.objects.create(api_info=api_info, mcp_tool_id=tool_id)
        ApiInfoMcpConfig.objects.create(
            api_info=api_info,
            mcp_tool_id=tool_id,
            mcp_config=None,
            input_schema=input_schema,
            output_schema=output_schema,
            schema_hash=ApiInfoRuntimeService.mcp_schema_hash(input_schema, output_schema),
        )
        return {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "api_info_id": api_info.id,
            "api_info_revision_id": None,
            "publication_status": "unpublished",
            "next_step": "先执行并验证接口；验证成功后再生成接口修订并发布。",
            "created": True,
        }
