from __future__ import annotations

from django.db.models import Q

from src.apps.task_center.enums.execution import (
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.services.diagnostic_markdown import DiagnosticMarkdownService
from src.apps.test_center.services.product_module import ProductModuleService
from src.interfaces.mcp.common import (
    fail,
    ok,
)

MAX_PAGE_SIZE = 100
MAX_DETAIL_CASES = 100
MAX_RECENT_FIRES = 10

from .helpers import (
    _case_summary,
    _effective_case_counts,
    _page,
    _recent_fire_summary,
    _scheduled_task_cases_queryset,
    _scheduled_task_queryset_for_user,
    _scheduled_task_summary,
)


def register_scheduled_task_query_tools(mcp):
    @mcp.tool()
    def list_scheduled_tasks(
            keyword: str | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            status: int | None = None,
            case_people_id: int | None = None,
            test_env: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询普通定时任务列表。支持按任务名、项目产品、模块、状态、负责人和测试环境过滤。"""
        page, page_size = _page(page, page_size)
        queryset = _scheduled_task_queryset_for_user()
        if keyword:
            queryset = queryset.filter(
                Q(name__contains=keyword)
                | Q(project_product__name__contains=keyword)
                | Q(project_product__project__name__contains=keyword)
                | Q(module__name__contains=keyword)
                | Q(timing_strategies__name__contains=keyword)
                | Q(timing_strategies__cron__contains=keyword)
            ).distinct()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if case_people_id is not None:
            queryset = queryset.filter(case_people_id=case_people_id)
        if test_env is not None:
            queryset = queryset.filter(test_envs__contains=[test_env])

        count = queryset.count()
        offset = (page - 1) * page_size
        tasks = list(queryset.order_by("-id")[offset: offset + page_size])
        case_counts = _effective_case_counts(tasks)
        return ok(
            {
                "items": [_scheduled_task_summary(item, case_counts) for item in tasks],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_scheduled_task_detail(
            task_id: int,
            include_cases: bool = True,
            case_limit: int = 10,
            case_page: int = 1,
            case_page_size: int | None = None,
    ) -> dict:
        """查询普通定时任务详情，包含任务配置、绑定用例摘要和最近触发记录。"""
        task = _scheduled_task_queryset_for_user().filter(id=task_id).first()
        if not task:
            return fail("定时任务不存在或当前用户无权查看。", "SCHEDULED_TASK_NOT_FOUND", {"task_id": task_id})

        case_counts = _effective_case_counts([task])
        data = _scheduled_task_summary(task, case_counts)
        if task.diagnostic_file_path:
            data["diagnostic_download_url"] = DiagnosticMarkdownService.metadata(
                DiagnosticMarkdownService.TARGET_SCHEDULED_TASK,
                task,
            )["download_url"]
        else:
            data["diagnostic_download_url"] = None
        data["recent_fires"] = [
            _recent_fire_summary(item)
            for item in ScheduleFireQuerySelector.schedule_fire().filter(task_id=task.id)
            .select_related("time_task", "task", "test_suite")
            .order_by("-planned_at", "-id")[:MAX_RECENT_FIRES]
        ]
        data["cases"] = []
        if include_cases:
            if case_page_size is None:
                case_page_size = case_limit
            case_page, case_page_size = _page(case_page, case_page_size)
            offset = (case_page - 1) * case_page_size
            if task.execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
                details_queryset = _scheduled_task_cases_queryset(task.id).order_by("id")
                count = details_queryset.count()
                details = details_queryset[offset: offset + case_page_size]
                data["cases"] = [_case_summary(item) for item in details]
                data["case_selection_source"] = "manual_binding"
            else:
                selected_cases = ScheduledTaskCaseSelectionService.select_task(task)
                count = len(selected_cases)
                data["cases"] = [
                    item.to_dict()
                    for item in selected_cases[offset: offset + case_page_size]
                ]
                data["case_selection_source"] = "dynamic_rule"
            data["cases_count"] = count
            data["case_page"] = case_page
            data["case_page_size"] = case_page_size
            data["case_limit"] = case_page_size
            data["case_truncated"] = count > case_page * case_page_size
        return ok(data)

    @mcp.tool()
    def list_scheduled_task_cases(
            task_id: int,
            type: int | None = None,
            keyword: str | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            case_people_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询普通定时任务绑定的 case 清单。用于完整比对 task 与 tag/case 绑定集合。"""
        task = _scheduled_task_queryset_for_user().filter(id=task_id).first()
        if not task:
            return fail("定时任务不存在或当前用户无权查看。", "SCHEDULED_TASK_NOT_FOUND", {"task_id": task_id})
        page, page_size = _page(page, page_size)
        if task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value:
            items = ScheduledTaskCaseSelectionService.select_task(task)
            if type is not None:
                items = [item for item in items if item.case_type == int(type)]
            if keyword:
                normalized_keyword = keyword.lower()
                items = [
                    item for item in items
                    if normalized_keyword in item.case_name.lower() or normalized_keyword in str(item.case_id)
                ]
            if module_id:
                module_ids = ProductModuleService.module_scope_ids(module_id)
                items = [item for item in items if item.module_id in module_ids]
            count = len(items)
            offset = (page - 1) * page_size
            return ok({
                "items": [item.to_dict() for item in items[offset:offset + page_size]],
                "count": count,
                "page": page,
                "page_size": page_size,
                "task": _scheduled_task_summary(task),
                "selection_source": "dynamic_rule",
            })
        queryset = _scheduled_task_cases_queryset(
            task_id=task.id,
            case_type=type,
            keyword=keyword,
            project_product_id=project_product_id,
            module_id=module_id,
            case_people_id=case_people_id,
        ).order_by("id")
        count = queryset.count()
        offset = (page - 1) * page_size
        details = queryset[offset: offset + page_size]
        return ok(
            {
                "items": [_case_summary(item) for item in details],
                "count": count,
                "page": page,
                "page_size": page_size,
                "task": _scheduled_task_summary(task, _effective_case_counts([task])),
            }
        )
