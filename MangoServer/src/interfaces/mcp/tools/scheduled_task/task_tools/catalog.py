from __future__ import annotations

from typing import Annotated

from django.db.models import Q
from pydantic import Field

from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.test_center.services.diagnostic_markdown import DiagnosticMarkdownService
from src.interfaces.mcp.common import (
    fail,
    ok,
)

MAX_PAGE_SIZE = 100
MAX_DETAIL_CASES = 100
MAX_RECENT_FIRES = 10

from .helpers import (
    _datetime_text,
    _page,
    _scheduled_task_queryset_for_user,
)


def register_scheduled_task_catalog_tools(mcp):
    @mcp.tool()
    def upload_scheduled_task_diagnostic_markdown(
            task_id: int,
            file_name: Annotated[
                str,
                Field(
                    pattern=r'.*\.[mM][dD]$',
                    description='Markdown 文件名，必须以 .md 结尾。',
                ),
            ],
            markdown_content: str,
    ) -> dict:
        """将 Codex 生成的 Markdown 排查报告绑定到定时任务。

        仅允许上传 .md 文件；负责上传和绑定现成报告，不在测试平台内执行诊断。
        相同任务再次上传时替换为最新报告。
        """
        task = _scheduled_task_queryset_for_user().filter(id=task_id).first()
        if not task:
            return fail(
                "定时任务不存在或当前用户无权访问。",
                "SCHEDULED_TASK_NOT_FOUND",
                {"task_id": task_id},
            )
        try:
            data = DiagnosticMarkdownService.save(
                DiagnosticMarkdownService.TARGET_SCHEDULED_TASK,
                task.id,
                file_name,
                markdown_content,
            )
        except TaskCenterError as exc:
            return fail(str(exc), "DIAGNOSTIC_MARKDOWN_UPLOAD_FAILED", {"task_id": task_id})
        return ok(data)

    @mcp.tool()
    def list_scheduled_task_strategies(
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询可用于普通定时任务的定时策略。"""
        page, page_size = _page(page, page_size)
        queryset = TaskCenterQuerySelector.time_tasks().all()
        if keyword:
            queryset = queryset.filter(Q(name__contains=keyword) | Q(cron__contains=keyword))
        count = queryset.count()
        offset = (page - 1) * page_size
        items = queryset.order_by("-id")[offset: offset + page_size]
        return ok({
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "cron": item.cron,
                    "create_time": _datetime_text(item.create_time),
                    "update_time": _datetime_text(item.update_time),
                }
                for item in items
            ],
            "count": count,
            "page": page,
            "page_size": page_size,
        })
