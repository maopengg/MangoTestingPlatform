from __future__ import annotations

from typing import Any

from src.apps.auto_api.models import (
    ApiHeaders,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.interfaces.mcp.audit import (
    mcp_current_user_id,
)
from src.interfaces.mcp.common import (
    current_user,
)
from src.interfaces.mcp.exceptions import MCP_TEST_ENVIRONMENT_REQUIRED, McpError

API_CASE_RESULT_EXPORT_RELATIVE_DIR = "mcp_export/api_case_result"
API_CASE_RESULT_EXPORT_RETENTION_DAYS = 7

FILE_UPLOAD_USAGE = {
    "description": "API 接口定义和 API case 场景参数中的 multipart.files 用于描述 multipart/form-data 文件参数。",
    "required_format": {"body_type": "multipart", "body_config": {"fields": [], "files": [
        {"key": "请求文件字段名", "file_id": 1, "file_name": "可选发送文件名"}]}},
    "strict_rule": "文件必须来自测试配置-测试文件中的 FileData.id，不能直接传本地路径、URL、裸文件名或二进制内容。",
    "workflow": [
        "先调用 system_file 分组的 upload_system_file 上传真实文件，记录返回的 file.name 或上传时传入的 name。",
        "在 body_config.files 中写入 file_id，并把 key 设置为接口要求的文件字段名。",
        "执行时后端会按 file_id 读取 FileData.test_file 并发送文件。",
    ],
    "example": {"body_type": "multipart", "body_config": {"fields": [{"key": "name", "value": "demo"}],
                                                          "files": [{"key": "file", "file_id": 1}]}},
    "notes": [
        "示例中的 key 是请求参数名；如果接口字段名叫 upload_file，则 key 写 upload_file。",
        "建议先用 list_system_files 查询确认 file_id 和项目产品是否匹配。",
        "远程 MCP 服务通常无法读取调用者本机路径，因此只接受 FileData.id。",
    ],
}


def _create_case_step(
        case_id: int,
        api_info_id: int,
        case_sort: int | None = None,
        *,
        record_config: bool = True,
        operator_id: int | None = None,
        pinned_api_info_revision_id: int | None = None,
        execution_config: dict | None = None,
) -> dict:
    if case_sort is None:
        case_sort = ApiQuerySelector.api_case_detailed().filter(case_id=case_id).count()

    def create_step(_):
        result = ApiCaseStepService.create_step_with_default_parameter(
            case_id=case_id,
            api_info_id=api_info_id,
            case_sort=case_sort,
            operator_id=operator_id or mcp_current_user_id(),
            pinned_api_info_revision_id=pinned_api_info_revision_id,
            execution_config=execution_config,
        )
        return {
            "step_id": result.step.id,
            "case_id": case_id,
            "api_info_id": api_info_id,
            "api_info_revision_id": result.api_info_revision_id,
            "case_sort": case_sort,
            "default_parameter_id": result.parameter.id,
        }

    if not record_config:
        return create_step(None)
    return ApiCaseAggregateMutationService.mutate(
        case_id,
        action="create_step",
        operation=create_step,
        operator_id=operator_id or mcp_current_user_id(),
        source="mcp",
    )


def _selected_env(user_id: int | None, test_env_id: int | None) -> int:
    if test_env_id is not None:
        return test_env_id
    user = current_user(user_id)
    from src.apps.user.services.user_cache import UserCacheService

    selected_environment = UserCacheService.selected_environment(user)
    if selected_environment is None:
        raise McpError(MCP_TEST_ENVIRONMENT_REQUIRED)
    return int(selected_environment)


def _find_json_paths(data: Any, prefix: str = "$", limit: int = 20) -> list[tuple[str, Any]]:
    paths: list[tuple[str, Any]] = []
    if len(paths) >= limit:
        return paths
    if isinstance(data, dict):
        for key, value in data.items():
            child_prefix = f"{prefix}.{key}"
            if isinstance(value, (dict, list)):
                paths.extend(_find_json_paths(value, child_prefix, limit - len(paths)))
            else:
                paths.append((child_prefix, value))
            if len(paths) >= limit:
                break
    elif isinstance(data, list) and data:
        paths.extend(_find_json_paths(data[0], f"{prefix}[0]", limit))
    return paths[:limit]


def _list_same_api_headers(project_product_id: int, key: str) -> list[ApiHeaders]:
    return list(
        ApiQuerySelector.api_headers().select_related("project_product")
        .filter(project_product_id=project_product_id, key__iexact=key)
        .order_by("-status", "-id")
    )


def _api_header_summary(header: ApiHeaders) -> dict:
    project_product = header.project_product
    return {
        "id": header.id,
        "project_product_id": header.project_product_id,
        "project_product_name": project_product.name if project_product else None,
        "api_client_type": getattr(project_product, "api_client_type", None) if project_product else None,
        "key": header.key,
        "value": header.value,
        "status": header.status,
    }
