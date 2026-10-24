from django.db import transaction

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_STEP_CASE_STEP_PAGE_ORDER_INVALID,
)
from src.apps.auto_ui.models import PageStepsDetailed, UiCaseStepsDetailed
from src.apps.auto_ui.services.flow_refresh import UiFlowRefreshService


class UiStepOrderingService:
    @staticmethod
    @transaction.atomic
    def sort_page_step_details(
            page_step_id: int,
            sort_items: list[dict],
            operator_id: int | None = None,
    ) -> list[dict]:
        normalized = [
            {"id": int(item["id"]), "step_sort": int(item["step_sort"])}
            for item in sort_items
        ]
        if not normalized or not page_step_id:
            raise AutoUiError(UI_STEP_CASE_STEP_PAGE_ORDER_INVALID)
        ids = [item["id"] for item in normalized]
        if PageStepsDetailed.objects.filter(
                id__in=ids,
                page_step_id=page_step_id,
        ).count() != len(set(ids)):
            raise AutoUiError(UI_STEP_CASE_STEP_PAGE_ORDER_INVALID)
        for item in normalized:
            detail = PageStepsDetailed.objects.select_for_update().get(
                id=item["id"],
                page_step_id=page_step_id,
            )
            detail.step_sort = item["step_sort"]
            update_fields = ["step_sort", "update_time"]
            if operator_id is not None:
                detail.update_user_id = operator_id
                update_fields.append("update_user")
            detail.save(update_fields=update_fields)
        UiFlowRefreshService.refresh_page_step(page_step_id)
        return normalized

    @staticmethod
    @transaction.atomic
    def sort_case_steps(
            case_id: int,
            sort_items: list[dict],
            operator_id: int | None = None,
    ) -> list[dict]:
        normalized = [
            {"id": int(item["id"]), "case_sort": int(item["case_sort"])}
            for item in sort_items
        ]
        if not normalized or not case_id:
            raise AutoUiError(UI_STEP_CASE_STEP_PAGE_ORDER_INVALID)
        ids = [item["id"] for item in normalized]
        if UiCaseStepsDetailed.objects.filter(
                id__in=ids,
                case_id=case_id,
        ).count() != len(set(ids)):
            raise AutoUiError(UI_STEP_CASE_STEP_PAGE_ORDER_INVALID)
        for item in normalized:
            detail = UiCaseStepsDetailed.objects.select_for_update().get(
                id=item["id"],
                case_id=case_id,
            )
            detail.case_sort = item["case_sort"]
            update_fields = ["case_sort", "update_time"]
            if operator_id is not None:
                detail.update_user_id = operator_id
                update_fields.append("update_user")
            detail.save(update_fields=update_fields)
        UiFlowRefreshService.refresh_case(case_id)
        return normalized
