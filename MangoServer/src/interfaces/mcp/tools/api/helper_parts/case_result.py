from __future__ import annotations

import json as jsonlib
import os
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.forms import model_to_dict
from django.utils import timezone

from src.apps.auto_api.formatters import format_api_case
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    fail,
)

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

from ..helpers import _api_case_version_summary, _api_info_revision_summary


def _case_owner_required() -> dict:
    return fail(
        "创建 API case 需要指定负责人 case_people_id，或通过 MCP APIKey/JWT 识别当前用户作为默认负责人。",
        "CASE_OWNER_REQUIRED",
        {
            "required_field": "case_people_id",
            "next_actions": [
                "在 MCP 客户端 Authorization 中配置当前用户 APIKey",
                "调用 list_case_owners 查询可选负责人",
                "向用户展示负责人列表并询问 case 要绑定给谁",
                "用户选择后再次调用 create_api_case 或 create_complete_api_case",
            ],
        },
    )


def _case_tree(case_id: int, include_result_data: bool = True) -> dict:
    from src.apps.auto_api.services.api_case.query import ApiCaseQueryService

    case = ApiCaseQueryService.get_instance(case_id)
    case_data = format_api_case(case)
    case_data.update(_api_case_version_summary(case_id))
    case_data.update(
        is_product_owner=TestCenterQuerySelector.is_project_product_owner(
            case.project_product_id, mcp_current_user_id(),
        ),
        has_product_owner=TestCenterQuerySelector.has_project_product_owner(case.project_product_id),
    )
    steps = []
    details = (
        ApiQuerySelector.api_case_detailed().select_related("api_info", "pinned_api_info_revision")
        .filter(case_id=case_id)
        .order_by("case_sort", "id")
    )
    for detail in details:
        api_info = ApiCaseStepService.resolve_step_api_runtime(detail, allow_draft=True)
        parameters = []
        for parameter in ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id=detail.id).order_by(
                "id"):
            parameter_data = model_to_dict(parameter)
            if include_result_data:
                parameter_data["result_data"] = ExecutionResultService.latest_api_case_parameter_result(
                    case_id=case_id,
                    parameter_id=parameter.id,
                ) or None
            parameters.append(parameter_data)
        detail_data = model_to_dict(detail)
        api_info_data = model_to_dict(api_info)
        api_info_data.update(ApiInfoRuntimeService.capture_runtime_payload(api_info))
        detail_data.update(_api_info_revision_summary(detail.pinned_api_info_revision))
        steps.append(
            {
                "detail": detail_data,
                "api_info": api_info_data,
                "parameters": parameters,
            }
        )
    return {"case": case_data, "steps": steps}


def _api_case_result_value_summary(value: Any, sample_limit: int = 5) -> dict:
    value_type = type(value).__name__
    summary = {
        "value_type": value_type,
        "count": None,
        "value": value,
        "sample": None,
        "truncated": False,
    }
    if isinstance(value, list):
        summary["count"] = len(value)
        summary["sample"] = value[:sample_limit]
        summary["truncated"] = len(value) > sample_limit
        summary["value"] = value if len(value) <= sample_limit else None
    elif isinstance(value, dict):
        summary["count"] = len(value)
        items = list(value.items())
        summary["sample"] = dict(items[:sample_limit])
        summary["truncated"] = len(items) > sample_limit
        summary["value"] = value if len(items) <= sample_limit else None
    elif isinstance(value, str):
        summary["count"] = len(value)
        summary["truncated"] = len(value) > 2000
        summary["value"] = value[:2000] if summary["truncated"] else value
    return summary


def _cleanup_api_case_result_exports():
    export_dir = os.path.join(settings.MEDIA_ROOT, API_CASE_RESULT_EXPORT_RELATIVE_DIR)
    if not os.path.isdir(export_dir):
        return
    expired_before = timezone.now() - timedelta(days=API_CASE_RESULT_EXPORT_RETENTION_DAYS)
    for file_name in os.listdir(export_dir):
        file_path = os.path.join(export_dir, file_name)
        if not os.path.isfile(file_path):
            continue
        try:
            modified_at = timezone.datetime.fromtimestamp(os.path.getmtime(file_path),
                                                          tz=timezone.get_current_timezone())
            if modified_at < expired_before:
                os.remove(file_path)
        except OSError:
            continue


def _export_api_case_result_value(
        value: Any,
        *,
        case_id: int,
        step_id: int | None,
        scenario_id: int | None,
        json_path: str | None,
) -> dict:
    _cleanup_api_case_result_exports()
    export_dir = os.path.join(settings.MEDIA_ROOT, API_CASE_RESULT_EXPORT_RELATIVE_DIR)
    os.makedirs(export_dir, exist_ok=True)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    file_name = f"api_case_{case_id}_step_{step_id or 'all'}_scenario_{scenario_id or 'all'}_{timestamp}_{uuid.uuid4().hex[:8]}.json"
    relative_path = f"{API_CASE_RESULT_EXPORT_RELATIVE_DIR}/{file_name}"
    file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    payload = {
        "case_id": case_id,
        "step_id": step_id,
        "scenario_id": scenario_id,
        "json_path": json_path,
        "export_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "retention_days": API_CASE_RESULT_EXPORT_RETENTION_DAYS,
        "value": value,
    }
    with open(file_path, "w", encoding="utf-8") as file:
        jsonlib.dump(payload, file, ensure_ascii=False, indent=2, default=str)
    return {
        "file_name": file_name,
        "relative_path": relative_path,
        "file_path": file_path,
        "download_url": f"{settings.MEDIA_URL.rstrip('/')}/{relative_path}",
        "file_size": os.path.getsize(file_path),
        "retention_days": API_CASE_RESULT_EXPORT_RETENTION_DAYS,
    }


def _parse_result_path(path: str) -> list[Any]:
    value = (path or "").strip()
    if not value:
        return []
    if value.startswith("$."):
        value = value[2:]
    elif value.startswith("$"):
        value = value[1:]
    tokens: list[Any] = []
    current = ""
    index = 0
    while index < len(value):
        char = value[index]
        if char == ".":
            if current:
                tokens.append(current)
                current = ""
            index += 1
            continue
        if char == "[":
            if current:
                tokens.append(current)
                current = ""
            end = value.find("]", index)
            if end == -1:
                tokens.append(value[index + 1:])
                break
            raw_index = value[index + 1:end].strip().strip("'\"")
            if raw_index.isdigit():
                tokens.append(int(raw_index))
            elif raw_index:
                tokens.append(raw_index)
            index = end + 1
            continue
        current += char
        index += 1
    if current:
        tokens.append(current)
    return tokens


def _get_result_path_value(data: Any, path: str) -> tuple[bool, Any, str | None]:
    current = data
    for token in _parse_result_path(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return False, None, f"列表索引不存在：{token}"
            current = current[token]
            continue
        if isinstance(current, dict) and token in current:
            current = current[token]
            continue
        return False, None, f"字段不存在：{token}"
    return True, current, None


def _api_case_step_result_items(
        case_id: int,
        step_id: int | None = None,
        scenario_id: int | None = None,
        step_name: str | None = None,
        json_path: str | None = None,
        sample_limit: int = 5,
        export_full: bool = False,
) -> dict:
    queryset = ApiQuerySelector.api_case_detailed_parameter().select_related(
        "case_detailed",
        "case_detailed__api_info",
    ).filter(
        case_detailed__case_id=case_id,
    ).order_by("case_detailed__case_sort", "case_detailed_id", "id")
    if step_id is not None:
        queryset = queryset.filter(case_detailed_id=step_id)
    if scenario_id is not None:
        queryset = queryset.filter(id=scenario_id)
    if step_name:
        queryset = queryset.filter(Q(name__contains=step_name) | Q(case_detailed__api_info__name__contains=step_name))
    items = []
    matched_count = queryset.count()
    for parameter in queryset[:50]:
        result_data = ExecutionResultService.latest_api_case_parameter_result(
            case_id=case_id,
            parameter_id=parameter.id,
        )
        value = result_data
        path_found = True
        path_error = None
        if json_path:
            path_found, value, path_error = _get_result_path_value(result_data, json_path)
        summary = _api_case_result_value_summary(value, sample_limit=sample_limit) if path_found else None
        export_file = None
        if export_full and path_found:
            export_file = _export_api_case_result_value(
                value,
                case_id=case_id,
                step_id=parameter.case_detailed_id,
                scenario_id=parameter.id,
                json_path=json_path,
            )
        items.append({
            "step_id": parameter.case_detailed_id,
            "step_name": parameter.case_detailed.api_info.name if parameter.case_detailed and parameter.case_detailed.api_info else None,
            "scenario_id": parameter.id,
            "scenario_name": parameter.name,
            "status": parameter.status,
            "has_result_data": bool(result_data),
            "json_path": json_path,
            "path_found": path_found,
            "path_error": path_error,
            "summary": summary,
            "export_file": export_file,
            "error_message": result_data.get("error_message") if isinstance(result_data, dict) else None,
            "test_time": result_data.get("test_time") if isinstance(result_data, dict) else None,
        })
    return {
        "case_id": case_id,
        "matched_count": matched_count,
        "returned_count": len(items),
        "items": items,
        "truncated": matched_count > len(items),
    }
