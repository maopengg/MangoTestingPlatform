from django.db import transaction
from src.apps.auto_api.models import ApiInfo, ApiInfoMcpConfig
from src.apps.auto_api.enums import ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.exceptions import protocol_error


class ApiInfoMcpImportService:
    @staticmethod
    @transaction.atomic
    def create(*, tool_name, server_url, input_schema, output_schema, project_product_id, module_id, operator_id,
               transport_type=0, tool_title=None):
        from urllib.parse import urlparse
        parsed = urlparse(server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not tool_name:
            raise protocol_error("请提供有效的 MCP 服务地址和工具名称")
        if transport_type != 0:
            raise protocol_error("仅支持 Streamable HTTP")
        from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
        info = ApiInfoMutationService.create_definition({"name": tool_title or tool_name,
            "project_product": project_product_id, "module": module_id,
            "protocol_type": ApiProtocolTypeEnum.MCP.value, "url": parsed.path or "/",
            "method": MethodEnum.MCP_CALL.value, "body_type": "json",
            "mcp_binding": {"server_url": server_url, "transport_type": transport_type,
                "tool_name": tool_name, "tool_type": "tool", "tool_enabled": True,
                "input_schema": input_schema, "output_schema": output_schema}}, operator_id=operator_id)
        return {"api_info_id": info.id, "tool_name": tool_name, "publication_status": "unpublished", "created": True}
