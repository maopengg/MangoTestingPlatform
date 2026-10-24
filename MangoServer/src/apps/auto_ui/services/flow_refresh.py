"""UI 步骤与用例流程摘要刷新。"""

from django.utils import timezone

from src.apps.auto_ui.models import UiCase, UiCaseStepsDetailed
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService


class UiFlowRefreshService:
    @staticmethod
    def refresh_page_step(page_step_id: int | None) -> None:
        if page_step_id is not None:
            PageStepDetailMutationService.refresh_run_flow(page_step_id)

    @staticmethod
    def refresh_case(case_id: int | None) -> None:
        if case_id is None:
            return
        names = []
        for item in UiCaseStepsDetailed.objects.filter(case_id=case_id).select_related(
                "page_step"
        ).order_by("case_sort"):
            names.append(item.page_step.name if item.page_step_id else "")
        UiCase.objects.filter(id=case_id).update(
            case_flow="".join(f"->{name}" for name in names),
            update_time=timezone.now(),
        )
