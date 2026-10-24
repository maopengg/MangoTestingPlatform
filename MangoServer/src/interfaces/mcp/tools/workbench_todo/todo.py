from __future__ import annotations

from src.apps.task_center.enums import WorkbenchTodoStatusEnum
from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
from src.interfaces.mcp.common import current_user, fail, ok, paginate_queryset

STATUS_VALUES = {
    "pending": WorkbenchTodoStatusEnum.PENDING.value,
    "handled": WorkbenchTodoStatusEnum.HANDLED.value,
}


def _visible_queryset():
    return WorkbenchTodoService.visible_queryset(current_user())


def _filtered_queryset(
        *,
        project_product_id: int | None = None,
        source_type: int | None = None,
        event_type: int | None = None,
        severity: int | None = None,
):
    queryset = _visible_queryset()
    if project_product_id is not None:
        queryset = queryset.filter(project_product_id=project_product_id)
    if source_type is not None:
        queryset = queryset.filter(source_type=source_type)
    if event_type is not None:
        queryset = queryset.filter(event_type=event_type)
    if severity is not None:
        queryset = queryset.filter(severity=severity)
    return queryset


def _status_value(status: str) -> int | None:
    return STATUS_VALUES.get(str(status or "pending").strip().lower())


def register_workbench_todo_tools(mcp):
    @mcp.tool()
    def list_workbench_todos(
            status: str = "pending",
            project_product_id: int | None = None,
            source_type: int | None = None,
            event_type: int | None = None,
            severity: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询当前用户有权查看的风险待办。status 支持 pending、handled、all。"""
        normalized_status = str(status or "pending").strip().lower()
        if normalized_status not in {*STATUS_VALUES, "all"}:
            return fail(
                "status 仅支持 pending、handled 或 all。",
                "WORKBENCH_TODO_STATUS_INVALID",
            )
        queryset = _filtered_queryset(
            project_product_id=project_product_id,
            source_type=source_type,
            event_type=event_type,
            severity=severity,
        )
        summary = WorkbenchTodoService.summary(queryset)
        status_value = _status_value(normalized_status)
        if status_value is not None:
            queryset = queryset.filter(status=status_value)
        rows, count, page, page_size = paginate_queryset(
            queryset,
            page=page,
            page_size=page_size,
            max_page_size=100,
        )
        return ok(
            {
                "summary": summary,
                "items": [WorkbenchTodoService.serialize(item) for item in rows],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_workbench_todo_detail(todo_id: int) -> dict:
        """查询单条风险待办及修复所需的来源资产、项目产品、负责人和异常详情。"""
        todo = _visible_queryset().filter(id=todo_id).first()
        if todo is None:
            return fail(
                "待办不存在或当前用户无权查看。",
                "WORKBENCH_TODO_NOT_FOUND",
                {"todo_id": todo_id},
            )
        return ok(WorkbenchTodoService.serialize(todo))

    @mcp.tool()
    def refresh_workbench_todos() -> dict:
        """触发风险待办状态同步，并返回当前用户可见的待处理汇总。修复底层资产后调用此工具复核自动关闭结果。"""
        reconciliation = WorkbenchTodoService.reconcile_todos()
        summary = WorkbenchTodoService.summary(_visible_queryset())
        return ok(
            {
                "reconciliation": reconciliation,
                "summary": summary,
            },
            "风险待办状态同步完成",
        )

    @mcp.tool()
    def update_workbench_todo_handled(todo_id: int, handle_note: str) -> dict:
        """逐条确认允许人工处理的风险待办。handle_note 必须写明实际处理动作和验证依据。"""
        note = str(handle_note or "").strip()
        if not note:
            return fail(
                "人工处理待办必须填写实际处理动作和验证依据。",
                "WORKBENCH_TODO_HANDLE_NOTE_REQUIRED",
                {"todo_id": todo_id},
            )
        user = current_user()
        todo = WorkbenchTodoService.visible_queryset(user).filter(id=todo_id).first()
        if todo is None:
            return fail(
                "待办不存在或当前用户无权处理。",
                "WORKBENCH_TODO_NOT_FOUND",
                {"todo_id": todo_id},
            )
        if not WorkbenchTodoService.can_mark_handled(todo):
            return fail(
                "该待办不允许人工确认，请修复底层资产后由系统自动关闭。",
                "WORKBENCH_TODO_MANUAL_HANDLE_FORBIDDEN",
                {"todo_id": todo_id},
            )
        if not WorkbenchTodoService.mark_handled(todo, user, note):
            return fail(
                "待办状态已变化，请刷新后重试。",
                "WORKBENCH_TODO_STATE_CHANGED",
                {"todo_id": todo_id},
            )
        return ok(WorkbenchTodoService.serialize(todo), "待办已标记为已处理")
