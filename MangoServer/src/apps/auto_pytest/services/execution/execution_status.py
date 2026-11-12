from datetime import datetime

from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_pytest.models import PytestCase


class PytestExecutionStatusService:
    """Project executor-task terminal states onto the Pytest case list."""

    @classmethod
    def project_status(cls, case_id: int, status: int) -> int:
        return PytestCase.objects.filter(
            id=case_id,
            status=TaskEnum.PROCEED.value,
        ).update(status=status, update_time=timezone.now())

    @classmethod
    def proceeding_case_candidates(cls, limit: int) -> list[tuple[int, datetime]]:
        return list(
            PytestCase.objects.filter(status=TaskEnum.PROCEED.value)
            .order_by("id")
            .values_list("id", "update_time")[:limit]
        )
