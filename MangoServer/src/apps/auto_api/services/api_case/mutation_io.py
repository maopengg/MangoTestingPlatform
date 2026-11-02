"""API Case 与场景参数的统一写入入口。

该服务供 REST、MCP 和其他后端调用方复用，不依赖 HTTP CRUD 类。
"""

from django.db import transaction

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import (
    API_CASE_PREPUBLICATION_PRODUCT_CHANGE_NOT_ALLOWED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter, ApiCaseRelease
from src.apps.auto_api.schemas.case_schema import (
    ApiEnvironmentKeyValueItem,
    validate_data_source_operation_list,
    validate_int_list,
    validate_model_list,
    validate_scenario_tag_list,
    ApiParametrizeSuite,
    merge_scenario_protocol_config,
)
from src.apps.auto_api.schemas.config_fields import API_CASE_CONFIG_FIELDS
from src.apps.auto_api.services.api_case.parameter_validation import (
    ApiCaseParameterValidationService,
)
from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService
from src.apps.auto_api.services.callback import ApiCallbackService
from src.apps.auto_api.services.config.version import (
    ApiConfigDiffService,
    ApiConfigSnapshotService,
)
from src.apps.test_center.formatters.related import format_product_module, format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED


class ApiCaseMutationService:
    IDENTITY_FIELDS = {
        "id",
        "project_product",
        "module",
        "update_user",
        "name",
        "case_flow",
        "case_people",
        "parametrize",
        "level",
        "scenario_layer",
        "scenario_type",
        "scenario_tags",
        "scenario_description",
        "status",
    }

    @classmethod
    def split_payload(cls, payload: dict) -> tuple[dict, dict]:
        identity = {key: value for key, value in payload.items() if key in cls.IDENTITY_FIELDS}
        config = {key: value for key, value in payload.items() if key in API_CASE_CONFIG_FIELDS}
        return identity, config

    @staticmethod
    def validate_config(config: dict, project_product_id=None) -> dict:
        validators = {
            "callback_checks": lambda value: ApiCallbackService.validate_config(value, project_product_id),
            "front_custom": lambda value: validate_model_list(value, ApiEnvironmentKeyValueItem, "前置方法"),
            "front_sql": lambda value: validate_data_source_operation_list(value, "前置数据库操作", project_product_id),
            "front_headers": lambda value: validate_int_list(value, "前置请求头"),
            "front_public": lambda value: validate_int_list(value, "用例选择全局变量"),
            "front_auth_config": lambda value: validate_int_list(value, "用例选择授权配置"),
            "posterior_sql": lambda value: validate_data_source_operation_list(value, "后置数据库操作",
                                                                               project_product_id),
        }
        return {key: validators[key](value) for key, value in config.items()}

    @staticmethod
    def _present(instance: ApiCase) -> dict:
        data = model_payload(instance)
        data["project_product"] = format_project_product(instance.project_product)
        data["module"] = format_product_module(instance.module)
        data["case_people"] = format_user(instance.case_people)
        data["update_user"] = format_user_simple(instance.update_user)
        config = ApiExecutableSnapshotService.current_case_config(
            instance.id,
            instance.project_product_id,
        )
        for field in API_CASE_CONFIG_FIELDS:
            data[field] = config.get(field, [])
        return data

    @classmethod
    @transaction.atomic
    def create(
            cls,
            payload: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
            source: str = "internal",
    ) -> dict:
        identity, config = cls.split_payload(dict(payload))
        config = cls.validate_config(config, identity.get("project_product"))
        if config.get('callback_checks'):
            from src.apps.auto_api.exceptions import API_CALLBACK_CONFIG_INVALID
            raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('请先创建用例及步骤，再配置回调验证',))
        if "parametrize" in identity:
            identity["parametrize"] = validate_model_list(identity["parametrize"], ApiParametrizeSuite, "参数化")
        if "scenario_tags" in identity:
            identity["scenario_tags"] = validate_scenario_tag_list(identity["scenario_tags"])
        ProductModuleService.validate_crud_binding(ApiCase, identity)
        if operator_id is not None:
            identity["update_user"] = operator_id
        try:
            instance = save_model(ApiCase, {**identity, **config})
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        if record_config:
            ApiConfigDiffService.record_instance_change(instance, action="create", source=source)
        return cls._present(instance)

    @classmethod
    @transaction.atomic
    def update(
            cls,
            case_id: int,
            payload: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
            source: str = "internal",
    ) -> dict:
        instance = ApiCase.objects.select_for_update().get(id=case_id)
        identity, config = cls.split_payload(dict(payload))
        target_project_product_id = identity.get("project_product")
        if isinstance(target_project_product_id, dict):
            target_project_product_id = target_project_product_id.get("id")
        elif hasattr(target_project_product_id, "pk"):
            target_project_product_id = target_project_product_id.pk
        try:
            normalized_project_product_id = (
                int(target_project_product_id)
                if target_project_product_id is not None
                else None
            )
        except (TypeError, ValueError):
            normalized_project_product_id = None
        if (
                ApiCaseRelease.objects.filter(
                    api_case_id=instance.id,
                    status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
                ).exists()
                and normalized_project_product_id is not None
                and normalized_project_product_id != instance.project_product_id
        ):
            raise AutoApiError(API_CASE_PREPUBLICATION_PRODUCT_CHANGE_NOT_ALLOWED)
        config = cls.validate_config(config, identity.get("project_product") or instance.project_product_id)
        if config.get('callback_checks') or instance.callback_checks:
            ApiCallbackService.validate_config(
                config.get('callback_checks', instance.callback_checks),
                normalized_project_product_id or instance.project_product_id, instance.id,
            )
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(instance).snapshot
        if "scenario_tags" in identity:
            identity["scenario_tags"] = validate_scenario_tag_list(identity["scenario_tags"])
        ProductModuleService.validate_crud_binding(ApiCase, identity, instance)
        if operator_id is not None:
            identity["update_user"] = operator_id
        try:
            instance = save_model(
                ApiCase,
                {**identity, **config},
                instance=instance,
                partial=True,
            )
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
        if record_config:
            ApiConfigDiffService.record_instance_change(
                instance,
                action="update",
                before_snapshot=before_snapshot,
                source=source,
            )
        return cls._present(instance)

    @staticmethod
    @transaction.atomic
    def delete(case_id: int) -> None:
        ApiCase.objects.select_for_update().get(id=case_id).delete()


class ApiCaseParameterMutationService:
    DEPRECATED_FIELDS = {
        "data",
        "json",
        "file",
        "protocol_type",
        "body_type",
        "mcp_config",
        "grpc_config",
        "protocol_expectation",
        "result_data",
    }

    @classmethod
    def clean_payload(cls, payload: dict) -> dict:
        cleaned = dict(payload)
        if any(field in cleaned for field in ("body_config", "mcp_config", "grpc_config", "protocol_expectation")):
            cleaned["body_config"] = merge_scenario_protocol_config(
                cleaned.get("body_config"),
                cleaned.get("mcp_config"),
                cleaned.get("grpc_config"),
                cleaned.get("protocol_expectation"),
            )
        for field in cls.DEPRECATED_FIELDS:
            cleaned.pop(field, None)
        return cleaned

    @classmethod
    @transaction.atomic
    def create(cls, payload: dict, *, record_config: bool = True, source: str = "internal") -> dict:
        data = ApiCaseParameterValidationService.validate(cls.clean_payload(payload))
        try:
            instance = save_model(ApiCaseDetailedParameter, data)
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        if record_config:
            ApiConfigDiffService.record_instance_change(instance, action="create", source=source)
        return model_payload(instance)

    @classmethod
    @transaction.atomic
    def update(
            cls,
            parameter_id: int,
            payload: dict,
            *,
            record_config: bool = True,
            source: str = "internal",
    ) -> dict:
        instance = ApiCaseDetailedParameter.objects.select_for_update().get(id=parameter_id)
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(instance).snapshot
        data = ApiCaseParameterValidationService.validate(
            cls.clean_payload(payload),
            instance,
        )
        try:
            instance = save_model(
                ApiCaseDetailedParameter,
                data,
                instance=instance,
                partial=True,
            )
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
        if record_config:
            ApiConfigDiffService.record_instance_change(
                instance,
                action="update",
                before_snapshot=before_snapshot,
                source=source,
            )
        return model_payload(instance)
