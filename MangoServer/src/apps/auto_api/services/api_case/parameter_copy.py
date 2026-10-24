"""Transactional copying for API case parameters."""

from django.forms import model_to_dict

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import merge_scenario_protocol_config
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.case_config import DataFactoryCaseConfigService
from src.common.database import ModelMutationValidationError, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED


class ApiCaseParameterCopyService:
    @classmethod
    def copy(
            cls,
            source_id: int,
            overrides: dict,
            *,
            operator_id: int | None = None,
    ) -> ApiCaseDetailedParameter:
        source = ApiCaseDetailedParameter.objects.select_related("case_detailed").get(id=source_id)

        def perform(_):
            locked = ApiCaseDetailedParameter.objects.select_for_update().get(id=source_id)
            payload = model_to_dict(locked)
            payload.pop("id", None)
            payload.update(
                name=overrides.get("name") or f"(副本){locked.name}",
                error_retry=overrides.get("error_retry"),
                retry_interval=overrides.get("retry_interval"),
                allow_failure=(
                    bool(overrides.get("allow_failure"))
                    if "allow_failure" in overrides
                    else locked.allow_failure
                ),
                body_config=merge_scenario_protocol_config(
                    payload.get("body_config"),
                    protocol_expectation=overrides.get("protocol_expectation"),
                ),
                status=2,
                update_user=operator_id,
            )
            payload = ApiCaseParameterValidationService.validate(payload)
            try:
                copied = save_model(ApiCaseDetailedParameter, payload)
            except ModelMutationValidationError as error:
                raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
            cls._copy_data_factory_configs(source_id, copied.id, operator_id)
            return copied

        return ApiCaseAggregateMutationService.mutate(
            source.case_detailed.case_id,
            action="copy_parameter",
            operation=perform,
            operator_id=operator_id,
            source="page",
        )

    @staticmethod
    def _copy_data_factory_configs(source_id: int, target_id: int, operator_id: int | None) -> None:
        source_type = DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value
        for config in DataFactoryCaseConfig.objects.filter(
                source_type=source_type,
                source_id=source_id,
        ).order_by("id"):
            payload = model_to_dict(config)
            payload.pop("id", None)
            payload.update(source_type=source_type, source_id=target_id)
            DataFactoryCaseConfigService.create(
                payload,
                update_user_id=operator_id,
                source="page",
            )


__all__ = ["ApiCaseParameterCopyService"]
