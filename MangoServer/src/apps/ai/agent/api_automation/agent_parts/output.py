# -*- coding: utf-8 -*-
from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.models import AiAgentTask, AiAgentTaskItem
from src.apps.ai.services.core import AiTaskService
from src.apps.functional_test.models import ManualTestCase


class ApiAutomationOutputMixin:
    @staticmethod
    def batch_summary(manual_case_snapshots: list[dict]) -> dict:
        total = len(manual_case_snapshots)
        bound_count = len([item for item in manual_case_snapshots if item.get("existing_api_case_id")])
        return {
            "total": total,
            "unbound_count": total - bound_count,
            "bound_count": bound_count,
        }

    @staticmethod
    def build_batch_items(task: AiAgentTask, ordered_cases: list[ManualTestCase]) -> list[dict]:
        task_items = {
            item.manual_case_id: item
            for item in AiAgentTaskItem.objects.filter(task=task)
        }
        status_names = {
            AiAgentTaskStatusEnum.PENDING.value: "pending",
            AiAgentTaskStatusEnum.CLAIMED.value: "pending",
            AiAgentTaskStatusEnum.RUNNING.value: "running",
            AiAgentTaskStatusEnum.SUCCESS.value: "success",
            AiAgentTaskStatusEnum.FAIL.value: "fail",
        }
        items = []
        for case in ordered_cases:
            task_item = task_items.get(case.id)
            items.append(
                {
                    "manual_case_id": case.id,
                    "case_no": case.case_no,
                    "title": case.title,
                    "status": status_names.get(getattr(task_item, "status", None), "pending"),
                    "api_case_id": getattr(task_item, "api_case_id", None),
                    "summary": (getattr(task_item, "result_summary", None) or {}).get("summary") or "",
                    "error_message": getattr(task_item, "error_message", None),
                }
            )
        return items

    @staticmethod
    def batch_output(task: AiAgentTask, items: list[dict], current_index: int, success_count: int,
                     fail_count: int) -> dict:
        input_data = task.input_data or {}
        return {
            "mode": "batch",
            "suite_id": input_data.get("suite_id"),
            "total": len(items),
            "current_index": current_index,
            "success_count": success_count,
            "fail_count": fail_count,
        }

    @classmethod
    def update_batch_progress(
            cls,
            task: AiAgentTask,
            items: list[dict],
            current_index: int,
            success_count: int,
            fail_count: int,
            detail: str,
    ):
        output = cls.batch_output(task, items, current_index, success_count, fail_count)
        task.output_data = {**(task.output_data or {}), **output}
        task.save(update_fields=["output_data", "update_time"])
        total = max(len(items), 1)
        percent = min(95, 10 + int((current_index / total) * 80))
        AiTaskService.update_progress(
            task,
            percent,
            "批量生成 API 自动化",
            detail,
            {
                "mode": "batch",
                "current_index": current_index,
                "total": len(items),
                "success_count": success_count,
                "fail_count": fail_count,
            },
        )

    @staticmethod
    def normalize_mcp_server_ids(values: list | tuple | None = None) -> list[int]:
        if values is None:
            values = []
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = []
        for value in values:
            try:
                server_id = int(value)
            except (TypeError, ValueError):
                continue
            if server_id and server_id not in normalized:
                normalized.append(server_id)
        return normalized
