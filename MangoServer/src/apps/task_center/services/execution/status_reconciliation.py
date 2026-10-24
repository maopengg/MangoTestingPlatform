from collections.abc import Callable
from datetime import datetime, timedelta

from django.db.models import Max
from django.utils import timezone
from mangotools.enums import TaskEnum
from math import ceil

from src.apps.system.enums import (
    ExecutorTaskStatusEnum,
    ServerApiCommandEnum,
    ServerPytestCommandEnum,
    ServerUiCommandEnum,
)
from src.apps.task_center.models import ExecutorTask


class ExecutionStatusProjectionService:
    """Keep denormalized business statuses aligned with executor-task facts."""

    RECONCILE_GRACE_SECONDS = 120
    RECONCILE_BATCH_SIZE = 200
    SUPPORTED_BUSINESS_TYPES = {
        ServerApiCommandEnum.API_CASE.value,
        ServerUiCommandEnum.CASE_BATCH.value,
        ServerUiCommandEnum.PAGE_STEPS.value,
        ServerPytestCommandEnum.TEST_CASE.value,
    }

    @classmethod
    def _has_newer_task(cls, task: ExecutorTask) -> bool:
        if task.business_id is None:
            return False
        return ExecutorTask.objects.filter(
            business_type=task.business_type,
            business_id=task.business_id,
            id__gt=task.id,
        ).exists()

    @staticmethod
    def _terminal_business_status(task: ExecutorTask) -> int:
        result_data = task.result_data if isinstance(task.result_data, dict) else {}
        result_status = result_data.get("status")
        try:
            normalized_status = int(result_status)
        except (TypeError, ValueError):
            normalized_status = None
        if normalized_status in {
            TaskEnum.FAIL.value,
            TaskEnum.SUCCESS.value,
            TaskEnum.WARNING.value,
        }:
            return normalized_status
        if task.status == ExecutorTaskStatusEnum.SUCCESS.value:
            return TaskEnum.SUCCESS.value
        return TaskEnum.FAIL.value

    @classmethod
    def project(cls, task: ExecutorTask, *, force_failure: bool = False) -> int:
        if task.business_id is None or task.business_type not in cls.SUPPORTED_BUSINESS_TYPES:
            return 0
        if cls._has_newer_task(task):
            return 0
        status = TaskEnum.FAIL.value if force_failure else cls._terminal_business_status(task)
        if task.business_type == ServerApiCommandEnum.API_CASE.value:
            from src.apps.auto_api.services.test_case.run_status import ApiCaseRunStatusService

            return ApiCaseRunStatusService.project_status(task.business_id, status)
        if task.business_type == ServerUiCommandEnum.CASE_BATCH.value:
            from src.apps.auto_ui.services.execution_status import UiExecutionStatusService

            return UiExecutionStatusService.project_case_status(task.business_id, status)
        if task.business_type == ServerUiCommandEnum.PAGE_STEPS.value:
            from src.apps.auto_ui.services.execution_status import UiExecutionStatusService

            return UiExecutionStatusService.project_page_step_status(task.business_id, status)
        if task.business_type == ServerPytestCommandEnum.TEST_CASE.value:
            from src.apps.auto_pytest.services.execution_status import PytestExecutionStatusService

            return PytestExecutionStatusService.project_status(task.business_id, status)
        return 0

    @classmethod
    def _latest_tasks(
            cls,
            business_type: str,
            business_ids: list[int],
    ) -> list[ExecutorTask]:
        if not business_ids:
            return []
        latest_ids = list(
            ExecutorTask.objects.filter(
                business_type=business_type,
                business_id__in=business_ids,
            )
            .values("business_id")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        return list(ExecutorTask.objects.filter(id__in=latest_ids).order_by("id"))

    @classmethod
    def _candidate_sources(
            cls,
    ) -> list[tuple[str, Callable[[int], list[tuple[int, datetime]]]]]:
        from src.apps.auto_api.services.test_case.run_status import ApiCaseRunStatusService
        from src.apps.auto_pytest.services.execution_status import PytestExecutionStatusService
        from src.apps.auto_ui.services.execution_status import UiExecutionStatusService

        return [
            (
                ServerApiCommandEnum.API_CASE.value,
                ApiCaseRunStatusService.proceeding_case_candidates,
            ),
            (
                ServerUiCommandEnum.CASE_BATCH.value,
                UiExecutionStatusService.proceeding_case_candidates,
            ),
            (
                ServerUiCommandEnum.PAGE_STEPS.value,
                UiExecutionStatusService.proceeding_page_step_candidates,
            ),
            (
                ServerPytestCommandEnum.TEST_CASE.value,
                PytestExecutionStatusService.proceeding_case_candidates,
            ),
        ]

    @classmethod
    def reconcile(cls, *, batch_size: int | None = None) -> dict[str, int]:
        limit = max(1, min(int(batch_size or cls.RECONCILE_BATCH_SIZE), 500))
        cutoff = timezone.now() - timedelta(seconds=cls.RECONCILE_GRACE_SECONDS)
        sources = cls._candidate_sources()
        per_source_limit = ceil(limit / len(sources))
        candidates: list[tuple[ExecutorTask, datetime]] = []
        for business_type, candidate_loader in sources:
            business_candidates = candidate_loader(per_source_limit)
            updated_at_map = dict(business_candidates)
            tasks = cls._latest_tasks(business_type, list(updated_at_map))
            candidates.extend((task, updated_at_map[task.business_id]) for task in tasks)
        projected = 0
        skipped = 0
        for task, business_updated_at in candidates[:limit]:
            if (
                    task.status not in ExecutorTaskStatusEnum.terminal_values()
                    or task.finished_at is None
                    or task.finished_at > cutoff
                    or business_updated_at > task.finished_at
            ):
                skipped += 1
                continue
            updated = cls.project(task)
            projected += updated
            skipped += int(updated == 0)
        return {
            "checked_count": min(len(candidates), limit),
            "projected_count": projected,
            "skipped_count": skipped,
            "grace_seconds": cls.RECONCILE_GRACE_SECONDS,
            "batch_size": limit,
        }
