from __future__ import annotations

from src.apps.auto_api.models import ApiCase
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)

MAX_PAGE_SIZE = 100
MAX_DETAIL_CASES = 100
MAX_RECENT_FIRES = 10

from .helpers import (
    _bind_case_ids,
    _bind_validation_failure,
    _build_bind_preview_data,
    _build_unbind_preview_data,
    _case_ids_target_id,
    _normalize_ids,
    _unbind_case_ids,
)


def register_scheduled_task_binding_tools(mcp):
    @mcp.tool()
    def preview_bind_cases_to_scheduled_task_impact(
            scheduled_task_id: int,
            ui_case_ids: list[int] | None = None,
            api_case_ids: list[int] | None = None,
    ) -> dict:
        """预览批量追加 UI/API Case 的影响，并校验任务限定的项目产品和模块。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not TaskCenterQuerySelector.tasks().filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})
        validation_failure = _bind_validation_failure(
            scheduled_task_id,
            ui_ids,
            api_ids,
        )
        if validation_failure:
            return validation_failure
        target_id = _case_ids_target_id(
            scheduled_task_id,
            ui_ids,
            api_ids,
        )
        confirm_text = f"BIND_CASES_TO_SCHEDULED_TASK:{target_id}"
        impact = _build_bind_preview_data(
            scheduled_task_id,
            ui_ids,
            api_ids,
        )
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
        """批量绑定 UI/API Case。Case 必须符合任务限定的项目产品和模块，且须先预览确认。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not TaskCenterQuerySelector.tasks().filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})
        validation_failure = _bind_validation_failure(
            scheduled_task_id,
            ui_ids,
            api_ids,
        )
        if validation_failure:
            return validation_failure
        target_id = _case_ids_target_id(
            scheduled_task_id,
            ui_ids,
            api_ids,
        )
        confirm_error = validate_dangerous_action_confirmation(
            "bind_cases_to_scheduled_task",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error

        user = current_user()
        created_ui, updated_ui, skipped_ui, missing_ui = _bind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=ui_ids,
            model=UiCase,
            case_field="ui_case_id",
            case_type=TestCaseTypeEnum.UI.value,
            update_user_id=user.id,
        )
        created_api, updated_api, skipped_api, missing_api = _bind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=api_ids,
            model=ApiCase,
            case_field="api_case_id",
            case_type=TestCaseTypeEnum.API.value,
            update_user_id=user.id,
        )

        data = {
            "scheduled_task_id": scheduled_task_id,
            "version_policy": ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
            "created_ui_case_ids": created_ui,
            "updated_ui_case_ids": updated_ui,
            "skipped_ui_case_ids": skipped_ui,
            "missing_ui_case_ids": missing_ui,
            "created_api_case_ids": created_api,
            "updated_api_case_ids": updated_api,
            "skipped_api_case_ids": skipped_api,
            "missing_api_case_ids": missing_api,
            "created_count": len(created_ui) + len(created_api),
            "updated_count": len(updated_ui) + len(updated_api),
            "skipped_count": len(skipped_ui) + len(skipped_api),
            "missing_count": len(missing_ui) + len(missing_api),
        }
        return ok(data, "定时任务 case 绑定完成")

    @mcp.tool()
    def preview_unbind_cases_from_scheduled_task_impact(
            scheduled_task_id: int,
            ui_case_ids: list[int] | None = None,
            api_case_ids: list[int] | None = None,
    ) -> dict:
        """预览从定时任务解除 UI/API case 绑定的影响，并生成确认 token。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not TaskCenterQuerySelector.tasks().filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})

        target_id = _case_ids_target_id(scheduled_task_id, ui_ids, api_ids)
        confirm_text = f"UNBIND_CASES_FROM_SCHEDULED_TASK:{target_id}"
        impact = _build_unbind_preview_data(scheduled_task_id, ui_ids, api_ids)
        return ok(
            create_dangerous_action_preview("unbind_cases_from_scheduled_task", target_id, confirm_text, impact),
            "已生成定时任务 case 解除绑定影响预览，请二次确认后执行",
        )

    @mcp.tool()
    def unbind_cases_from_scheduled_task(
            scheduled_task_id: int,
            ui_case_ids: list[int] | None = None,
            api_case_ids: list[int] | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """批量解除 UI/API case 与定时任务的绑定。必须先调用 preview_unbind_cases_from_scheduled_task_impact。"""
        ui_ids = _normalize_ids(ui_case_ids)
        api_ids = _normalize_ids(api_case_ids)
        if not ui_ids and not api_ids:
            return fail("ui_case_ids 和 api_case_ids 不能同时为空。", "CASE_IDS_EMPTY")
        if not TaskCenterQuerySelector.tasks().filter(id=scheduled_task_id).exists():
            return fail("定时任务不存在。", "SCHEDULED_TASK_NOT_FOUND", {"scheduled_task_id": scheduled_task_id})
        target_id = _case_ids_target_id(scheduled_task_id, ui_ids, api_ids)
        confirm_error = validate_dangerous_action_confirmation(
            "unbind_cases_from_scheduled_task",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error

        unbound_ui, skipped_ui, missing_ui = _unbind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=ui_ids,
            model=UiCase,
            case_field="ui_case_id",
            case_type=TestCaseTypeEnum.UI.value,
        )
        unbound_api, skipped_api, missing_api = _unbind_case_ids(
            scheduled_task_id=scheduled_task_id,
            case_ids=api_ids,
            model=ApiCase,
            case_field="api_case_id",
            case_type=TestCaseTypeEnum.API.value,
        )

        data = {
            "scheduled_task_id": scheduled_task_id,
            "unbound_ui_case_ids": unbound_ui,
            "skipped_ui_case_ids": skipped_ui,
            "missing_ui_case_ids": missing_ui,
            "unbound_api_case_ids": unbound_api,
            "skipped_api_case_ids": skipped_api,
            "missing_api_case_ids": missing_api,
            "unbound_count": len(unbound_ui) + len(unbound_api),
            "skipped_count": len(skipped_ui) + len(skipped_api),
            "missing_count": len(missing_ui) + len(missing_api),
        }
        return ok(data, "定时任务 case 解除绑定完成")
