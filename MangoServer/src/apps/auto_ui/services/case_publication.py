from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.exceptions.definitions import (
    UI_CASE_PUBLICATION_INVALID_TRANSITION, UI_CASE_PUBLICATION_OWNER_REQUIRED,
    UI_CASE_PUBLICATION_REQUIRES_PASSED, UI_CASE_PUBLICATION_NOT_FOUND,
)
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.selectors.case_publication import UiCasePublicationSelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector


class UiCasePublicationService:
    @staticmethod
    @transaction.atomic
    def transition(case_id: int, target_status: str, *, operator_id: int | None):
        case = UiCase.objects.select_for_update().filter(id=case_id).first()
        if case is None:
            raise AutoUiError(UI_CASE_PUBLICATION_NOT_FOUND)
        status = UiCasePublicationSelector.status(case)
        statuses = UiCasePublicationStatusEnum
        if target_status not in statuses.get_key_list() or target_status == status:
            raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
        if target_status in (statuses.PREPUBLISHED.value, statuses.PUBLISHED.value):
            if case.status != StatusEnum.SUCCESS.value:
                raise AutoUiError(UI_CASE_PUBLICATION_REQUIRES_PASSED)
        if target_status == statuses.PREPUBLISHED.value:
            if status != statuses.UNPUBLISHED.value:
                raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
            if not TestCenterQuerySelector.has_project_product_owner(case.project_product_id):
                raise AutoUiError(UI_CASE_PUBLICATION_OWNER_REQUIRED)
        else:
            if not TestCenterQuerySelector.is_project_product_owner(case.project_product_id, operator_id):
                raise AutoUiError(UI_CASE_PUBLICATION_OWNER_REQUIRED)
            if target_status == statuses.PUBLISHED.value and status != statuses.PREPUBLISHED.value:
                raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
        case.publication_status = target_status
        case.save(update_fields=['publication_status', 'update_time'])
        return case
