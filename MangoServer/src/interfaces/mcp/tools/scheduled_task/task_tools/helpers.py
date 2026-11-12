from __future__ import annotations

from django.db.models import Count, Q
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.common import (
    current_user,
    fail,
)

MAX_PAGE_SIZE = 100
MAX_DETAIL_CASES = 100
MAX_RECENT_FIRES = 10


def _page(page: int = 1, page_size: int = 10) -> tuple[int, int]:
    try:
        page = max(int(page or 1), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(max(int(page_size or 10), 1), MAX_PAGE_SIZE)
    except (TypeError, ValueError):
        page_size = 10
    return page, page_size


def _datetime_text(value) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _enum_name(enum_cls, value):
    return enum_cls.obj().get(value)


def _scheduled_task_queryset_for_user():
    queryset = TaskCenterQuerySelector.tasks().select_related(
        "project_product",
        "project_product__project",
        "module",
        "case_people",
        "notice_group",
    ).prefetch_related("timing_strategies").all()
    user = current_user()
    if (
            PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
    ):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()


def _notice_group_summary(notice_group) -> dict | None:
    if not notice_group:
        return None
    return {
        "id": notice_group.id,
        "name": notice_group.name,
        "project_id": notice_group.project_id,
        "mail": notice_group.mail,
        "feishu_configured": bool(notice_group.feishu),
        "dingding_configured": bool(notice_group.dingding),
        "work_weixin_configured": bool(notice_group.work_weixin),
    }


def _scheduled_task_summary(task: Tasks, case_counts: dict[int, dict] | None = None) -> dict:
    counts = case_counts.get(task.id, {}) if case_counts else {}
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "status_name": _enum_name(TaskEnum, task.status),
        "test_envs": task.test_envs,
        "test_env_names": [_enum_name(EnvironmentEnum, value) for value in task.test_envs],
        "case_types": task.case_types,
        "case_type_names": (
            [_enum_name(TestCaseTypeEnum, value) for value in task.case_types]
            if task.case_types else ["全部类型"]
        ),
        "execution_scenes": ScheduledTaskCaseSelectionService.task_execution_scenes(task),
        "execution_scene_names": [
            _enum_name(AutomationExecutionSceneEnum, value)
            for value in ScheduledTaskCaseSelectionService.task_execution_scenes(task)
        ],
        "execution_scope": task.execution_scope,
        "execution_scope_name": _enum_name(AutomationExecutionScopeEnum, task.execution_scope),
        "project_product_id": task.project_product_id,
        "project_product_name": task.project_product.name if task.project_product else None,
        "project_id": task.project_product.project_id if task.project_product else None,
        "project_name": task.project_product.project.name if task.project_product and task.project_product.project else None,
        "module_id": task.module_id,
        "module_name": task.module.name if task.module else None,
        "timing_strategies": [
            {
                "id": timing_strategy.id,
                "name": timing_strategy.name,
                "cron": timing_strategy.cron,
            }
            for timing_strategy in task.timing_strategies.all()
        ],
        "case_people": {
            "id": task.case_people_id,
            "name": task.case_people.name if task.case_people else None,
            "username": task.case_people.username if task.case_people else None,
        },
        "is_notice": task.is_notice,
        "fail_notice": task.fail_notice,
        "report_retention_policy": task.report_retention_policy,
        "api_concurrency_limit": task.api_concurrency_limit,
        "notice_group": _notice_group_summary(task.notice_group),
        "case_counts": {
            "ui": counts.get(TestCaseTypeEnum.UI.value, 0),
            "api": counts.get(TestCaseTypeEnum.API.value, 0),
            "pytest": counts.get(TestCaseTypeEnum.PYTEST.value, 0),
            "total": sum(counts.values()) if counts else 0,
        },
        "create_time": _datetime_text(task.create_time),
        "update_time": _datetime_text(task.update_time),
    }


def _case_summary(detail: TasksDetails) -> dict:
    case = detail.ui_case or detail.api_case or detail.pytest_case
    if not case:
        return {
            "detail_id": detail.id,
            "type": detail.type,
            "type_name": _enum_name(TestCaseTypeEnum, detail.type),
            "case_id": None,
            "case_name": None,
        }
    project_product = getattr(case, "project_product", None)
    if detail.type == TestCaseTypeEnum.PYTEST.value and project_product:
        project_product_id = getattr(project_product, "project_product_id", None)
        project_product_name = project_product.project_product.name if project_product.project_product else None
    else:
        project_product_id = getattr(case, "project_product_id", None)
        project_product_name = project_product.name if project_product else None
    case_people = getattr(case, "case_people", None)
    module = getattr(case, "module", None)
    return {
        "detail_id": detail.id,
        "type": detail.type,
        "type_name": _enum_name(TestCaseTypeEnum, detail.type),
        "case_id": case.id,
        "case_name": getattr(case, "name", None),
        "status": getattr(case, "status", None),
        "status_name": _enum_name(TaskEnum, getattr(case, "status", None)),
        "project_product_id": project_product_id,
        "project_product_name": project_product_name,
        "module_id": getattr(case, "module_id", None),
        "module_name": module.name if module else None,
        "case_people_id": getattr(case, "case_people_id", None),
        "case_people_name": case_people.name if case_people else None,
        "version_policy": (
            ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED
            if detail.type == TestCaseTypeEnum.API.value
            else None
        ),
        "api_case_revision_id": (
            detail.api_case_revision_id
            if detail.type == TestCaseTypeEnum.API.value
            else None
        ),
        "api_case_release_id": (
            detail.api_case_release_id
            if detail.type == TestCaseTypeEnum.API.value
            else None
        ),
    }


def _recent_fire_summary(fire: ScheduleFire) -> dict:
    return {
        "id": fire.id,
        "time_task_id": fire.time_task_id,
        "task_id": fire.task_id,
        "task_name": fire.task_name,
        "test_suite_id": fire.test_suite_id,
        "fire_key": fire.fire_key,
        "planned_at": _datetime_text(fire.planned_at),
        "fired_at": _datetime_text(fire.fired_at),
        "source_type": fire.source_type,
        "source_type_name": _enum_name(ScheduleFireSourceTypeEnum, fire.source_type),
        "status": fire.status,
        "status_name": _enum_name(ScheduleFireStatusEnum, fire.status),
        "trigger_node": fire.trigger_node,
        "dispatcher_node": fire.dispatcher_node,
        "error_message": fire.error_message,
    }


def _case_counts_for_tasks(task_ids: list[int]) -> dict[int, dict]:
    counts: dict[int, dict] = {task_id: {} for task_id in task_ids}
    if not task_ids:
        return counts
    rows = (
        TaskCenterQuerySelector.tasks_details().filter(task_id__in=task_ids)
        .values("task_id", "type")
        .annotate(total=Count("id"))
    )
    for row in rows:
        counts.setdefault(row["task_id"], {})[row["type"]] = row["total"]
    return counts


def _effective_case_counts(tasks: list[Tasks]) -> dict[int, dict]:
    counts = _case_counts_for_tasks([task.id for task in tasks])
    for task in tasks:
        if task.execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            continue
        task_counts: dict[int, int] = {}
        for item in ScheduledTaskCaseSelectionService.select_task(task):
            task_counts[item.case_type] = task_counts.get(item.case_type, 0) + 1
        counts[task.id] = task_counts
    return counts


def _scheduled_task_cases_queryset(
        task_id: int,
        case_type: int | None = None,
        keyword: str | None = None,
        project_product_id: int | None = None,
        module_id: int | None = None,
        case_people_id: int | None = None,
):
    queryset = TaskCenterQuerySelector.tasks_details().filter(task_id=task_id).select_related(
        "ui_case",
        "ui_case__project_product",
        "ui_case__module",
        "ui_case__case_people",
        "api_case",
        "api_case__project_product",
        "api_case__module",
        "api_case__case_people",
        "pytest_case",
        "pytest_case__project_product",
        "pytest_case__project_product__project_product",
        "pytest_case__module",
        "pytest_case__case_people",
    )
    if case_type is not None:
        queryset = queryset.filter(type=case_type)
    if keyword:
        queryset = queryset.filter(
            Q(ui_case__name__contains=keyword)
            | Q(api_case__name__contains=keyword)
            | Q(pytest_case__name__contains=keyword)
        )
    if project_product_id is not None:
        queryset = queryset.filter(
            Q(ui_case__project_product_id=project_product_id)
            | Q(api_case__project_product_id=project_product_id)
            | Q(pytest_case__project_product__project_product_id=project_product_id)
        )
    if module_id is not None:
        queryset = queryset.filter(
            Q(ui_case__module_id=module_id)
            | Q(api_case__module_id=module_id)
            | Q(pytest_case__module_id=module_id)
        )
    if case_people_id is not None:
        queryset = queryset.filter(
            Q(ui_case__case_people_id=case_people_id)
            | Q(api_case__case_people_id=case_people_id)
            | Q(pytest_case__case_people_id=case_people_id)
        )
    return queryset


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


def _case_ids_target_id(
        scheduled_task_id: int,
        ui_ids: list[int],
        api_ids: list[int],
) -> str:
    return (
        f"{scheduled_task_id}:ui={','.join(map(str, ui_ids))}:"
        f"api={','.join(map(str, api_ids))}"
    )


def _inspect_case_ids(
        scheduled_task_id: int,
        case_ids: list[int],
        model,
        case_field: str,
) -> tuple[list[int], list[int], list[int], list[int], list[int], list[int], list[int]]:
    case_type = (
        TestCaseTypeEnum.API.value
        if case_field == "api_case_id"
        else TestCaseTypeEnum.UI.value
    )
    result = TaskCaseBindingService.inspect_bind(
        scheduled_task_id,
        case_type,
        case_ids,
    )
    existing_result = (
        result.updated_ids
        if case_type == TestCaseTypeEnum.API.value
        else result.skipped_ids
    )
    return (
        result.created_ids,
        existing_result,
        result.missing_ids,
        result.product_mismatched_ids,
        result.module_mismatched_ids,
        result.type_mismatched_ids,
        result.unpublished_ids,
    )


def _inspect_unbind_case_ids(
        scheduled_task_id: int,
        case_ids: list[int],
        model,
        case_field: str,
) -> tuple[list[int], list[int], list[int]]:
    case_type = (
        TestCaseTypeEnum.API.value
        if case_field == "api_case_id"
        else TestCaseTypeEnum.UI.value
    )
    result = TaskCaseBindingService.inspect_unbind(
        scheduled_task_id,
        case_type,
        case_ids,
    )
    return result.removed_ids, result.skipped_ids, result.missing_ids


def _bind_case_ids(
        scheduled_task_id: int,
        case_ids: list[int],
        model,
        case_field: str,
        case_type: int,
        update_user_id: int | None = None,
) -> tuple[list[int], list[int], list[int], list[int]]:
    result = TaskCaseBindingService.bind(
        scheduled_task_id,
        case_type,
        case_ids,
        update_user_id=update_user_id,
    )
    return (
        result.created_ids,
        result.updated_ids,
        result.skipped_ids,
        result.missing_ids + result.mismatched_ids + result.unpublished_ids,
    )


def _unbind_case_ids(
        scheduled_task_id: int,
        case_ids: list[int],
        model,
        case_field: str,
        case_type: int,
) -> tuple[list[int], list[int], list[int]]:
    result = TaskCaseBindingService.unbind(
        scheduled_task_id,
        case_type,
        case_ids,
    )
    return result.removed_ids, result.skipped_ids, result.missing_ids


def _build_bind_preview_data(
        scheduled_task_id: int,
        ui_ids: list[int],
        api_ids: list[int],
) -> dict:
    (
        will_create_ui,
        skipped_ui,
        missing_ui,
        product_mismatched_ui,
        module_mismatched_ui,
        type_mismatched_ui,
        unpublished_ui,
    ) = _inspect_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=ui_ids,
        model=UiCase,
        case_field="ui_case_id",
    )
    (
        will_create_api,
        will_update_api,
        missing_api,
        product_mismatched_api,
        module_mismatched_api,
        type_mismatched_api,
        unpublished_api,
    ) = _inspect_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=api_ids,
        model=ApiCase,
        case_field="api_case_id",
    )
    return {
        "scheduled_task_id": scheduled_task_id,
        "version_policy": ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
        "will_create_ui_case_ids": will_create_ui,
        "skipped_ui_case_ids": skipped_ui,
        "missing_ui_case_ids": missing_ui,
        "product_mismatched_ui_case_ids": product_mismatched_ui,
        "module_mismatched_ui_case_ids": module_mismatched_ui,
        "will_create_api_case_ids": will_create_api,
        "will_update_api_case_ids": will_update_api,
        "skipped_api_case_ids": [],
        "missing_api_case_ids": missing_api,
        "product_mismatched_api_case_ids": product_mismatched_api,
        "module_mismatched_api_case_ids": module_mismatched_api,
        "type_mismatched_ui_case_ids": type_mismatched_ui,
        "type_mismatched_api_case_ids": type_mismatched_api,
        "unpublished_ui_case_ids": unpublished_ui,
        "unpublished_api_case_ids": unpublished_api,
        "will_create_count": len(will_create_ui) + len(will_create_api),
        "will_update_count": len(will_update_api),
        "skipped_count": len(skipped_ui),
        "missing_count": len(missing_ui) + len(missing_api),
        "scope_mismatched_count": (
                len(product_mismatched_ui)
                + len(module_mismatched_ui)
                + len(product_mismatched_api)
                + len(module_mismatched_api)
        ),
        "type_mismatched_count": len(type_mismatched_ui) + len(type_mismatched_api),
        "unpublished_count": len(unpublished_ui) + len(unpublished_api),
        "risk": (
            "确认后会向定时任务明细追加绑定 UI/API case；"
            "已有 API 绑定会更新为当前已发布版本策略；不存在、未发布或不符合任务用例类型、项目产品、模块范围的 case 会导致绑定失败。"
        ),
    }


def _bind_validation_failure(
        scheduled_task_id: int,
        ui_ids: list[int],
        api_ids: list[int],
) -> dict | None:
    ui_result = TaskCaseBindingService.inspect_bind(
        scheduled_task_id,
        TestCaseTypeEnum.UI.value,
        ui_ids,
    )
    api_result = TaskCaseBindingService.inspect_bind(
        scheduled_task_id,
        TestCaseTypeEnum.API.value,
        api_ids,
    )
    data = {
        "missing_ui_case_ids": ui_result.missing_ids,
        "missing_api_case_ids": api_result.missing_ids,
        "product_mismatched_ui_case_ids": ui_result.product_mismatched_ids,
        "product_mismatched_api_case_ids": api_result.product_mismatched_ids,
        "module_mismatched_ui_case_ids": ui_result.module_mismatched_ids,
        "module_mismatched_api_case_ids": api_result.module_mismatched_ids,
        "type_mismatched_ui_case_ids": ui_result.type_mismatched_ids,
        "type_mismatched_api_case_ids": api_result.type_mismatched_ids,
        "unpublished_ui_case_ids": ui_result.unpublished_ids,
        "unpublished_api_case_ids": api_result.unpublished_ids,
    }
    if ui_result.type_mismatched_ids or api_result.type_mismatched_ids:
        return fail(
            "定时任务已限定用例类型，存在其他类型的 Case，禁止绑定。",
            "SCHEDULED_TASK_CASE_TYPE_MISMATCH",
            data,
        )
    if ui_result.product_mismatched_ids or api_result.product_mismatched_ids:
        return fail(
            "定时任务已限定项目产品，存在不属于该项目产品的 Case，禁止绑定。",
            "SCHEDULED_TASK_CASE_PROJECT_PRODUCT_MISMATCH",
            data,
        )
    if ui_result.module_mismatched_ids or api_result.module_mismatched_ids:
        return fail(
            "定时任务已限定模块，存在不属于该模块的 Case，禁止绑定。",
            "SCHEDULED_TASK_CASE_MODULE_MISMATCH",
            data,
        )
    if ui_result.missing_ids or api_result.missing_ids:
        return fail(
            "部分 Case 不存在或已被删除，请刷新后重新选择。",
            "SCHEDULED_TASK_CASE_NOT_FOUND",
            data,
        )
    if ui_result.unpublished_ids or api_result.unpublished_ids:
        return fail(
            "部分 Case 尚未发布，请先发布后再绑定到定时任务。",
            "SCHEDULED_TASK_CASE_UNPUBLISHED",
            data,
        )
    return None


def _build_unbind_preview_data(scheduled_task_id: int, ui_ids: list[int], api_ids: list[int]) -> dict:
    will_unbind_ui, skipped_ui, missing_ui = _inspect_unbind_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=ui_ids,
        model=UiCase,
        case_field="ui_case_id",
    )
    will_unbind_api, skipped_api, missing_api = _inspect_unbind_case_ids(
        scheduled_task_id=scheduled_task_id,
        case_ids=api_ids,
        model=ApiCase,
        case_field="api_case_id",
    )
    return {
        "scheduled_task_id": scheduled_task_id,
        "will_unbind_ui_case_ids": will_unbind_ui,
        "skipped_ui_case_ids": skipped_ui,
        "missing_ui_case_ids": missing_ui,
        "will_unbind_api_case_ids": will_unbind_api,
        "skipped_api_case_ids": skipped_api,
        "missing_api_case_ids": missing_api,
        "will_unbind_count": len(will_unbind_ui) + len(will_unbind_api),
        "skipped_count": len(skipped_ui) + len(skipped_api),
        "missing_count": len(missing_ui) + len(missing_api),
        "risk": "确认后会从定时任务明细移除指定 UI/API case 绑定；不会删除 case 本身，不影响其他未指定绑定。",
    }
