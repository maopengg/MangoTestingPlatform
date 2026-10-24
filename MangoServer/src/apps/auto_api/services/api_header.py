from django.db.models import BooleanField, F, Func, JSONField, Value
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import (
    API_HEADER_REQUEST_DELETE_INVALID,
    API_HEADER_SCENARIO_REQUEST_DELETE_INVALID,
    API_HEADER_PROJECT_PRODUCT_REQUEST_DELETE_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter, ApiHeaders
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED


class ApiHeaderDeleteService:

    @classmethod
    def validate_batch(cls, headers):
        product_ids = {header.project_product_id for header in headers}
        if len(product_ids) != 1:
            raise AutoApiError(API_HEADER_PROJECT_PRODUCT_REQUEST_DELETE_INVALID)
        if any(header.status == StatusEnum.SUCCESS.value for header in headers):
            raise AutoApiError(API_HEADER_REQUEST_DELETE_INVALID)
        header_ids = [header.id for header in headers]
        if cls._has_usage(next(iter(product_ids)), header_ids):
            raise AutoApiError(API_HEADER_SCENARIO_REQUEST_DELETE_INVALID)

    @staticmethod
    def _json_overlaps(field_name, values):
        return Func(
            F(field_name),
            Value(values, output_field=JSONField()),
            function='JSON_OVERLAPS',
            output_field=BooleanField(),
        )

    @classmethod
    def _has_usage(cls, project_product_id, header_ids):
        case_usage_exists = (
            ApiCase.objects
            .filter(project_product_id=project_product_id)
            .annotate(_uses_selected_headers=cls._json_overlaps('front_headers', header_ids))
            .filter(_uses_selected_headers=True)
            .exists()
        )
        if case_usage_exists:
            return True
        return (
            ApiCaseDetailedParameter.objects
            .filter(case_detailed__case__project_product_id=project_product_id)
            .annotate(_uses_selected_headers=cls._json_overlaps('headers', header_ids))
            .filter(_uses_selected_headers=True)
            .exists()
        )


class ApiHeaderMutationService:
    @staticmethod
    def create(payload: dict, *, operator_id: int | None = None) -> dict:
        data = dict(payload)
        if operator_id is not None:
            data["update_user"] = operator_id
        try:
            return model_payload(save_model(ApiHeaders, data))
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error

    @staticmethod
    def update(header_id: int, payload: dict, *, operator_id: int | None = None) -> dict:
        instance = ApiHeaders.objects.get(id=header_id)
        data = dict(payload)
        if operator_id is not None:
            data["update_user"] = operator_id
        try:
            return model_payload(save_model(ApiHeaders, data, instance=instance, partial=True))
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
