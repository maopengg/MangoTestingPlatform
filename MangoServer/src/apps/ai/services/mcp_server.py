from dataclasses import dataclass

from src.apps.ai.enums import AiMcpUseTypeEnum
from src.apps.ai.models import AiMcpServer
from src.apps.ai.services.core import McpService
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.database import ModelMutationValidationError, save_model


@dataclass
class AiMcpServerMutationResult:
    instance: AiMcpServer | None = None
    errors: dict | None = None
    sync_result: dict | None = None
    test_result: dict | None = None
    sync_error: str | None = None


class AiMcpServerMutationService:
    @staticmethod
    def _validate(server: AiMcpServer | None, data: dict) -> dict:
        errors = {}
        if "prompt" in data:
            prompt = str(data.get("prompt") or "").strip()
            if not prompt:
                errors["prompt"] = ["MCP使用提示词不能为空"]
            else:
                data["prompt"] = prompt
        project_product_id = data.get(
            "project_product",
            server.project_product_id if server else None,
        )
        module_id = data.get("module", server.module_id if server else None)
        module = TestCenterQuerySelector.product_module().filter(id=module_id).first() if module_id else None
        if module and project_product_id and module.project_product_id != int(project_product_id):
            errors["module"] = ["模块不属于当前项目/产品"]
        if module and not project_product_id:
            errors["project_product"] = ["选择模块时必须选择项目/产品"]
        target_type = data.get("type", server.type if server else None)
        if (
                server
                and target_type == AiMcpUseTypeEnum.PLATFORM.value
                and ApiQuerySelector.api_info_mcp_binding().filter(mcp_tool__server=server).exists()
        ):
            errors["type"] = ["MCP服务已导入API自动化接口，不能改为平台调用"]
        return errors

    @staticmethod
    def _merge_auth_config(server: AiMcpServer, payload: dict) -> dict:
        data = dict(payload)
        auth_config = data.get("auth_config")
        if not isinstance(auth_config, dict):
            return data
        merged = dict(server.auth_config or {})
        for key, value in auth_config.items():
            if value != "***":
                merged[key] = value
        data["auth_config"] = merged
        return data

    @classmethod
    def create(
            cls,
            payload: dict,
            user_id: int | None,
            sync_after_save: bool = False,
            test_env: int | None = None,
    ) -> AiMcpServerMutationResult:
        data = dict(payload)
        if user_id is not None:
            data["create_user"] = user_id
            data["update_user"] = user_id
        errors = cls._validate(None, data)
        if errors:
            return AiMcpServerMutationResult(errors=errors)
        try:
            server = save_model(AiMcpServer, data)
        except ModelMutationValidationError as error:
            return AiMcpServerMutationResult(errors=error.errors)
        result = AiMcpServerMutationResult(instance=server)
        if sync_after_save:
            cls._sync_into_result(result, user_id, test_env)
        return result

    @classmethod
    def update(
            cls,
            server_id: int,
            payload: dict,
            user_id: int | None,
            sync_after_save: bool = False,
            test_env: int | None = None,
    ) -> AiMcpServerMutationResult:
        server = AiMcpServer.objects.get(id=server_id)
        data = cls._merge_auth_config(server, payload)
        if user_id is not None:
            data["update_user"] = user_id
        errors = cls._validate(server, data)
        if errors:
            return AiMcpServerMutationResult(errors=errors)
        try:
            server = save_model(AiMcpServer, data, instance=server, partial=True)
        except ModelMutationValidationError as error:
            return AiMcpServerMutationResult(errors=error.errors)
        result = AiMcpServerMutationResult(instance=server)
        if sync_after_save:
            cls._sync_into_result(result, user_id, test_env)
        return result

    @staticmethod
    def _sync_into_result(
            result: AiMcpServerMutationResult,
            user_id: int | None,
            test_env: int | None,
    ):
        try:
            result.test_result = McpService.test_server(result.instance, user_id)
            if result.test_result.get("ok"):
                result.sync_result = McpService.sync_tools(
                    result.instance,
                    user_id,
                    test_env=test_env,
                )
        except Exception as error:
            result.sync_error = str(error)

    @classmethod
    def sync_tools(
            cls,
            server_id: int,
            user_id: int | None,
            test_env: int | None = None,
    ) -> AiMcpServerMutationResult:
        result = AiMcpServerMutationResult(
            instance=AiMcpServer.objects.get(id=server_id)
        )
        cls._sync_into_result(result, user_id, test_env)
        return result
