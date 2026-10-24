"""Transactional copy operations for UI automation assets."""

from django.db import transaction
from django.forms import model_to_dict
from mangotools.enums import StatusEnum

from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum
from src.apps.auto_ui.models import PageSteps, PageStepsDetailed, UiCase, UiCaseStepsDetailed
from src.common.database import ModelMutationValidationError, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED


class UiAssetCopyService:
    @staticmethod
    def _clone(instance, *, overrides: dict):
        payload = model_to_dict(instance)
        payload.pop(instance._meta.pk.name, None)
        payload.update(overrides)
        try:
            return save_model(type(instance), payload)
        except ModelMutationValidationError as error:
            raise AutoUiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error

    @classmethod
    @transaction.atomic
    def copy_case(cls, case_id: int, *, operator_id: int | None = None) -> UiCase:
        source = UiCase.objects.select_for_update().get(id=case_id)
        copied = cls._clone(
            source,
            overrides={
                "name": f"(副本){source.name}",
                "status": StatusEnum.FAIL.value,
                "publication_status": UiCasePublicationStatusEnum.UNPUBLISHED.value,
                "update_user": operator_id,
            },
        )
        for step in UiCaseStepsDetailed.objects.filter(case_id=source.id).order_by("id"):
            cls._clone(step, overrides={"case": copied.id, "update_user": operator_id})
        return copied

    @classmethod
    @transaction.atomic
    def copy_page_steps(cls, page_step_id: int, *, operator_id: int | None = None) -> PageSteps:
        source = PageSteps.objects.select_for_update().get(id=page_step_id)
        copied = cls._clone(
            source,
            overrides={
                "name": f"(副本){source.name}",
                "type": StatusEnum.FAIL.value,
                "update_user": operator_id,
            },
        )
        for step in PageStepsDetailed.objects.filter(page_step_id=source.id).order_by("id"):
            cls._clone(step, overrides={"page_step": copied.id, "update_user": operator_id})
        return copied


__all__ = ["UiAssetCopyService"]
