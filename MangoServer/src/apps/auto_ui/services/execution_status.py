from datetime import datetime

from django.db.models import Max
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed


class UiExecutionStatusService:
    """Project executor-task terminal states without owning task recovery policy."""

    @classmethod
    def project_case_status(cls, case_id: int, status: int) -> int:
        now = timezone.now()
        updated = UiCase.objects.filter(
            id=case_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=now)
        updated += UiCaseStepsDetailed.objects.filter(
            case_id=case_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=now)
        return updated

    @classmethod
    def project_page_step_status(cls, page_step_id: int, status: int) -> int:
        return PageSteps.objects.filter(
            id=page_step_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=timezone.now())

    @classmethod
    def proceeding_case_candidates(cls, limit: int) -> list[tuple[int, datetime]]:
        candidates = {
            case_id: update_time
            for case_id, update_time in (
                UiCase.objects.filter(status=TaskEnum.PROCEED.value)
                .order_by("id")
                .values_list("id", "update_time")[:limit]
            )
        }
        detailed_cases = UiCaseStepsDetailed.objects.filter(
            status=TaskEnum.PROCEED.value,
        ).values("case_id").annotate(
            latest_update_time=Max("update_time"),
        ).order_by("case_id").values_list(
            "case_id", "latest_update_time",
        )[:limit]
        for case_id, update_time in detailed_cases:
            current = candidates.get(case_id)
            if current is None or update_time > current:
                candidates[case_id] = update_time
        return list(candidates.items())[:limit]

    @classmethod
    def proceeding_page_step_candidates(cls, limit: int) -> list[tuple[int, datetime]]:
        return list(
            PageSteps.objects.filter(status=TaskEnum.PROCEED.value)
            .order_by("id")
            .values_list("id", "update_time")[:limit]
        )
