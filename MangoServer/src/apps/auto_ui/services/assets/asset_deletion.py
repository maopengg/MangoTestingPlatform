from src.apps.auto_ui.models import (
    PageStepsDetailed,
    UiCaseStepsDetailed,
)
from src.apps.auto_ui.services.page_steps.flow_refresh import UiFlowRefreshService
from src.apps.auto_ui.services.page_steps.page_step_flow_service import PageStepFlowService


class UiAssetDeletionService:
    @staticmethod
    def delete(model, item_id: int) -> dict:
        if model is PageStepsDetailed:
            return UiAssetDeletionService.delete_page_step_details([item_id])

        parent_id = None
        if model is UiCaseStepsDetailed:
            parent_id = model.objects.values_list("case_id", flat=True).get(id=item_id)
        model.objects.get(id=item_id).delete()
        if model is UiCaseStepsDetailed and parent_id:
            UiFlowRefreshService.refresh_case(parent_id)
        return {"id": item_id}

    @staticmethod
    def delete_page_step_details(
            detail_ids: list[int],
            page_step_id: int | None = None,
    ) -> dict:
        affected_step_ids = set(
            PageStepsDetailed.objects.filter(id__in=detail_ids).values_list(
                "page_step_id",
                flat=True,
            )
        )
        if page_step_id:
            affected_step_ids.add(int(page_step_id))
        result = PageStepFlowService.delete_details(detail_ids, page_step_id)
        for target_step_id in affected_step_ids:
            UiFlowRefreshService.refresh_page_step(target_step_id)
        return result
