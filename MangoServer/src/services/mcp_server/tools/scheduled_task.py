from __future__ import annotations

from src.apps.auto_api.models import ApiCase
from src.apps.auto_ui.models import UiCase
from src.apps.system.models import Tasks, TasksDetails
from src.common.enums.tools_enum import TestCaseTypeEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


def _normalize_ids(values) -> list[int]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    normalized = []
    seen = set()
    for value in values:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item <= 0 or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _bind_target_id(scheduled_task_id: int, ui_ids: list[int], api_ids: list[int]) -> str:
    return f"{scheduled_task_id}:ui={','.join(map(str, ui_ids))}:api={','.join(map(str, api_ids))}"


def _inspect_case_ids(
    scheduled_task_id: int,
    case_ids: list[int],
    model,
    case_field: str,
) -> tuple[list[int], list[int], list[int]]:
    if not case_ids:
        return [], [], []

    existing_case_ids = set(model.objects.filter(id__in=case_ids).values_list("id", flat=True))
    missing_case_ids = [case_id for case_id in case_ids if case_id not in existing_case_ids]
    bound_case_ids = set(
        TasksDetails.objects.filter(task_id=scheduled_task_id, **{f"{case_field}__in": existing_case_ids}).values_list(
            case_field,
            flat=True,
        )
    )
    will_create_case_ids = [case_id for case_id in case_ids if case_id in existing_case_ids and case_id not in bound_case_ids]
    skipped_case_ids = [case_id for case_id in case_ids if case_id in bound_case_ids]
    return will_create_case_ids, skipped_case_ids, missing_case_ids


def _bind_case_ids(
    scheduled_task_id: int,
    case_ids: list[int],
    model,
    case_field: str,
    case_type: int,
) -> tuple[list[int], list[int], list[int]]:
    if not case_ids:
        return [], [], []

    existing_case_ids = set(model.objects.filter(id__in=case_ids).values_list("id", flat=True))
    missing_case_ids = [case_id for case_id in case_ids if case_id not in existing_case_ids]
    bound_case_ids = set(
        TasksDetails.objects.filter(task_id=scheduled_task_id, **{f"{case_field}__in": existing_case_ids}).values_list(
            case_field,
            flat=True,
        )
    )

    created_case_ids = []
    skipped_case_ids = []
    for case_id in case_ids:
        if case_id not in existing_case_ids:
            continue
        if case_id in bound_case_ids:
            skipped_case_ids.append(case_id)
            continue
        _, created = TasksDetails.objects.get_or_create(
            task_id=scheduled_task_id,
            type=case_type,
            **{case_field: case_id},
        )
        if created:
            created_case_ids.append(case_id)
        else:
            skipped_case_ids.append(case_id)

    return created_case_ids, skipped_case_ids, missing_case_ids


def _build_bind_preview_data(scheduled_task_id: int, ui_ids: list[int], api_ids: list[int]) -> dict:
    will_create_ui, skipped_ui, missing_ui = _inspect_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=ui_ids,
        model=UiCase,
        case_field="ui_case_id",
    )
    will_create_api, skipped_api, missing_api = _inspect_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=api_ids,
        model=ApiCase,
        case_field="api_case_id",
    )
    return {
        "scheduled_task_id": scheduled_task_id,
        "will_create_ui_case_ids": will_create_ui,
        "skipped_ui_case_ids": skipped_ui,
        "missing_ui_case_ids": missing_ui,
        "will_create_api_case_ids": will_create_api,
        "skipped_api_case_ids": skipped_api,
        "missing_api_case_ids": missing_api,
        "will_create_count": len(will_create_ui) + len(will_create_api),
        "skipped_count": len(skipped_ui) + len(skipped_api),
        "missing_count": len(missing_ui) + len(missing_api),
        "risk": "确认后会向定时任务明细追加绑定 UI/API case；已有绑定不会重复创建，缺失 case 不会绑定。",
    }


def register_scheduled_task_tools(mcp):
    @mcp.tool()
    def preview_bind_cases_to_scheduled_task_impact(
        scheduled_task_id: int,
        ui_case_ids: list[int] | None = None,
        api_case_ids: list[int] | None = None,
    ) -> dict:
        """预览批量追加 UI/API case 到定时任务的影响，并生成确认 token。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not Tasks.objects.filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})

        target_id = _bind_target_id(scheduled_task_id, ui_ids, api_ids)
        confirm_text = f"BIND_CASES_TO_SCHEDULED_TASK:{target_id}"
        impact = _build_bind_preview_data(scheduled_task_id, ui_ids, api_ids)
        return ok(
            create_dangerous_action_preview("bind_cases_to_scheduled_task", target_id, confirm_text, impact),
            "已生成定时任务 case 绑定影响预览，请二次确认后执行",
        )

    @mcp.tool()
    def bind_cases_to_scheduled_task(
        scheduled_task_id: int,
        ui_case_ids: list[int] | None = None,
        api_case_ids: list[int] | None = None,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """批量追加绑定 UI/API case 到定时任务。必须先调用 preview_bind_cases_to_scheduled_task_impact。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not Tasks.objects.filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})
        target_id = _bind_target_id(scheduled_task_id, ui_ids, api_ids)
        confirm_error = validate_dangerous_action_confirmation(
            "bind_cases_to_scheduled_task",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error

        created_ui, skipped_ui, missing_ui = _bind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=ui_ids,
            model=UiCase,
            case_field="ui_case_id",
            case_type=TestCaseTypeEnum.UI.value,
        )
        created_api, skipped_api, missing_api = _bind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=api_ids,
            model=ApiCase,
            case_field="api_case_id",
            case_type=TestCaseTypeEnum.API.value,
        )

        data = {
            "scheduled_task_id": scheduled_task_id,
            "created_ui_case_ids": created_ui,
            "skipped_ui_case_ids": skipped_ui,
            "missing_ui_case_ids": missing_ui,
            "created_api_case_ids": created_api,
            "skipped_api_case_ids": skipped_api,
            "missing_api_case_ids": missing_api,
            "created_count": len(created_ui) + len(created_api),
            "skipped_count": len(skipped_ui) + len(skipped_api),
            "missing_count": len(missing_ui) + len(missing_api),
        }
        return ok(data, "定时任务 case 绑定完成")
