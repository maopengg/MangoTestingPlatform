"""Transactional API case aggregate copying."""

from django.db import transaction
from django.forms import model_to_dict
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.case_config import DataFactoryCaseConfigService
from src.common.database import ModelMutationValidationError, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED


class ApiCaseCopyService:
    @staticmethod
    def _clone(instance, *, overrides: dict):
        payload = model_to_dict(instance)
        payload.pop(instance._meta.pk.name, None)
        payload.update(overrides)
        try:
            return save_model(type(instance), payload)
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error

    @classmethod
    @transaction.atomic
    def copy(cls, case_id: int, *, operator_id: int | None = None) -> ApiCase:
        source = ApiCase.objects.select_for_update().get(id=case_id)
        copied = cls._clone(
            source,
            overrides={
                "name": f"(副本){source.name}",
                "status": StatusEnum.FAIL.value,
                "update_user": operator_id,
            },
        )
        for source_step in ApiCaseDetailed.objects.filter(case_id=source.id).order_by("id"):
            copied_step = cls._clone(source_step, overrides={"case": copied.id, "update_user": operator_id})
            for source_parameter in ApiCaseDetailedParameter.objects.filter(
                    case_detailed_id=source_step.id,
            ).order_by("id"):
                copied_parameter = cls._clone(
                    source_parameter,
                    overrides={"case_detailed": copied_step.id, "update_user": operator_id},
                )
                cls._copy_data_factory_configs(
                    DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                    source_parameter.id,
                    copied_parameter.id,
                    operator_id,
                )
        cls._copy_data_factory_configs(
            DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source.id,
            copied.id,
            operator_id,
        )
        ApiCaseAggregateMutationService.rebuild_case_flow(copied.id)
        copied.refresh_from_db()
        return copied

    @staticmethod
    def _copy_data_factory_configs(
            source_type: int,
            source_id: int,
            target_id: int,
            operator_id: int | None,
    ) -> None:
        for config in DataFactoryCaseConfig.objects.filter(
                source_type=source_type,
                source_id=source_id,
        ).order_by("id"):
            payload = model_to_dict(config)
            payload.pop("id", None)
            payload.update({"source_type": source_type, "source_id": target_id})
            DataFactoryCaseConfigService.create(
                payload,
                update_user_id=operator_id,
                source="page",
            )


__all__ = ["ApiCaseCopyService"]
