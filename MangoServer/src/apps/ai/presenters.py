"""AI App 的协议无关输出转换，供 MCP 等非 HTTP 入口使用。"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from src.apps.ai.enums import AiMcpStatusEnum
from src.apps.ai.services.core import McpService, mask_sensitive


def _json_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


def _model_fields(instance) -> dict:
    return {
        field.name: _json_value(field.value_from_object(instance))
        for field in instance._meta.concrete_fields
    }


def _format_user(instance):
    if instance is None:
        return None
    return {"id": instance.id, "name": instance.name, "username": instance.username}


def _format_project_product(instance):
    if instance is None:
        return None
    project = getattr(instance, "project", None)
    return {
        "id": instance.id,
        "name": instance.name,
        "project": {"id": project.id, "name": project.name} if project is not None else None,
    }


def _format_module(instance):
    if instance is None:
        return None
    return {
        "id": instance.id,
        "name": instance.name,
        "level": instance.level,
        "full_path": instance.get_full_path(),
        "project_product_id": instance.project_product_id,
        "parent_id": instance.parent_id,
    }


def format_skill(instance, *, many=False):
    if many:
        return [format_skill(item) for item in instance]
    data = _model_fields(instance)
    data["user"] = _format_user(instance.user) if instance.user_id else None
    data["update_user"] = _format_user(instance.update_user) if instance.update_user_id else None
    return data


def format_agent_task(instance, *, many=False):
    if many:
        return [format_agent_task(item) for item in instance]
    data = _model_fields(instance)
    data["skill"] = format_skill(instance.skill) if instance.skill_id else None
    data["create_user"] = _format_user(instance.create_user) if instance.create_user_id else None
    data["input_data"] = mask_sensitive(data.get("input_data") or {})
    data["output_data"] = mask_sensitive(data.get("output_data") or {})
    if (instance.input_data or {}).get("mode") == "batch":
        status_names = {0: "fail", 1: "success", 2: "pending", 3: "running", 7: "pending", 8: "running"}
        case_snapshots = {
            item.get("id"): item
            for item in (instance.input_data or {}).get("manual_case_snapshots") or []
        }
        items = []
        for item in getattr(instance, "_presenter_items", ()):
            snapshot = case_snapshots.get(item.manual_case_id) or {}
            items.append({
                "manual_case_id": item.manual_case_id,
                "case_no": snapshot.get("case_no") or "",
                "title": snapshot.get("title") or "",
                "status": status_names.get(item.status, "pending"),
                "api_case_id": item.api_case_id,
                "summary": (item.result_summary or {}).get("summary") or "",
                "error_message": item.error_message or "",
            })
        data["output_data"] = {**(data.get("output_data") or {}), "items": items}
    return data


def format_agent_context(instance, *, many=False):
    if many:
        return [format_agent_context(item) for item in instance]
    data = _model_fields(instance)
    data["task"] = format_agent_task(instance.task) if instance.task_id else None
    data["create_user"] = _format_user(instance.create_user) if instance.create_user_id else None
    return data


def format_mcp_server(instance, *, many=False):
    if many:
        return [format_mcp_server(item) for item in instance]
    data = _model_fields(instance)
    data["auth_config"] = mask_sensitive(data.get("auth_config") or {})
    data["project_product"] = _format_project_product(instance.project_product) if instance.project_product_id else None
    data["module"] = _format_module(instance.module) if instance.module_id else None
    data["create_user"] = _format_user(instance.create_user) if instance.create_user_id else None
    data["update_user"] = _format_user(instance.update_user) if instance.update_user_id else None
    auth_config = instance.auth_config or {}
    data["is_builtin"] = bool(auth_config.get("builtin"))
    data["is_builtin_local"] = bool(auth_config.get("builtin_local"))
    data["is_builtin_manual"] = bool(auth_config.get("builtin_manual"))
    data["is_connected"] = bool(
        instance.status == AiMcpStatusEnum.ENABLED.value
        and instance.last_test_time
        and not instance.last_error
    )
    return data


def format_mcp_tool(instance, *, many=False):
    if many:
        return [format_mcp_tool(item) for item in instance]
    data = _model_fields(instance)
    data["server"] = format_mcp_server(instance.server) if instance.server_id else None
    data["project_product"] = _format_project_product(instance.project_product) if instance.project_product_id else None
    data["module"] = _format_module(instance.module) if instance.module_id else None
    data["effective_project_product_id"] = instance.project_product_id or getattr(instance.server, "project_product_id",
                                                                                  None)
    data["effective_module_id"] = instance.module_id or getattr(instance.server, "module_id", None)
    data["update_user"] = _format_user(instance.update_user) if instance.update_user_id else None
    category = McpService.tool_category(instance.name)
    data["category"] = category["key"]
    data["category_title"] = category["title"]
    try:
        binding = instance.api_info_binding
    except ObjectDoesNotExist:
        binding = None
    data["api_info_binding"] = {"api_info_id": binding.api_info_id} if binding is not None else None
    return data


def format_agent_task_step(instance, *, many=False):
    if many:
        return [format_agent_task_step(item) for item in instance]
    data = _model_fields(instance)
    data["task"] = format_agent_task(instance.task) if instance.task_id else None
    data["input_data"] = mask_sensitive(data.get("input_data") or {})
    data["output_data"] = mask_sensitive(data.get("output_data") or {})
    return data


def format_agent_tool_call(instance, *, many=False):
    if many:
        return [format_agent_tool_call(item) for item in instance]
    data = _model_fields(instance)
    data["task"] = format_agent_task(instance.task) if instance.task_id else None
    data["server"] = format_mcp_server(instance.server) if instance.server_id else None
    data["arguments"] = mask_sensitive(data.get("arguments") or {})
    data["result"] = mask_sensitive(data.get("result") or {})
    return data
