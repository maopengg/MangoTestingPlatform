"""API 定义写入服务。"""

from django.core.exceptions import FieldDoesNotExist
from django.db import transaction

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    API_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED,
    API_VERSION_API_INFO_NOT_FOUND,
    AUTO_API_DYNAMIC_ERROR,
    AutoApiError,
)
from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.schemas.case_schema import normalize_body_config_by_type, validate_body_config
from src.apps.auto_api.schemas.config_fields import API_INFO_CONFIG_FIELDS
from src.apps.auto_api.services.api_info.config import ApiInfoConfigService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.config.version import ApiConfigDiffService
from src.apps.auto_api.services.config.version import ApiConfigSnapshotService
from src.apps.test_center.services.product_module import ProductModuleService
from src.common.database import ModelMutationValidationError, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED


class ApiInfoMutationService:
    IDENTITY_FIELDS = {"id", "project_product", "module", "name", "update_user"}

    @classmethod
    def split_payload(cls, payload: dict) -> tuple[dict, dict]:
        identity = {key: value for key, value in payload.items() if key in cls.IDENTITY_FIELDS}
        config = {key: value for key, value in payload.items() if key in API_INFO_CONFIG_FIELDS}
        if "posterior_response" in payload:
            config["posterior_json_path"] = payload.get("posterior_response")
        if "posterior_response_text" in payload:
            config["posterior_re"] = payload.get("posterior_response_text")
        if config.get("body_config") is not None:
            body_type = config.get("body_type") or payload.get("body_type") or ApiBodyTypeEnum.NONE.value
            config["body_config"] = normalize_body_config_by_type(body_type, config["body_config"])
        if config.get("sse_config") is not None:
            config["sse_config"] = validate_body_config(config["sse_config"], "SSE配置")
        return identity, config

    @staticmethod
    def model_payload(identity: dict, config: dict) -> dict:
        model_field_names = {field.name for field in ApiInfo._meta.concrete_fields}
        return {
            **identity,
            **{key: value for key, value in config.items() if key in model_field_names},
        }

    @classmethod
    def create_definition(
            cls,
            payload: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
    ) -> ApiInfo:
        identity, config = cls.split_payload(payload)
        model_values = cls.model_payload(identity, config)
        effective_url = model_values.get("url", config.get("url"))
        effective_method = config.get("method")
        effective_protocol_type = (
                model_values.get("protocol_type")
                or config.get("protocol_type")
                or ApiProtocolTypeEnum.HTTP.value
        )
        effective_body_type = (
            ApiBodyTypeEnum.JSON.value
            if effective_protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value
            else config.get("body_type") or ApiBodyTypeEnum.NONE.value
        )
        cls._validate_definition(
            project_product_id=identity.get("project_product"),
            module_id=identity.get("module"),
            url=effective_url,
            method=effective_method,
            protocol_type=effective_protocol_type,
            body_type=effective_body_type,
        )
        model_values["url"] = effective_url
        model_values["protocol_type"] = effective_protocol_type
        return cls.create_validated(
            model_values,
            config,
            operator_id=operator_id,
            record_config=record_config,
        )

    @classmethod
    def update_definition(
            cls,
            api_info_id: int,
            payload: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
    ) -> ApiInfo:
        instance = ApiInfo.objects.get(pk=api_info_id)
        identity, config = cls.split_payload(payload)
        model_values = cls.model_payload(identity, config)
        current_runtime = ApiInfoRuntimeService.resolve_runtime(instance.id, allow_draft=True)
        effective_url = model_values.get("url", config.get("url", current_runtime.url))
        effective_method = config.get("method", current_runtime.method)
        effective_protocol_type = (
                model_values.get("protocol_type")
                or config.get("protocol_type")
                or current_runtime.protocol_type
        )
        effective_body_type = (
            ApiBodyTypeEnum.JSON.value
            if effective_protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value
            else config.get("body_type", current_runtime.body_type) or ApiBodyTypeEnum.NONE.value
        )
        cls._validate_definition(
            project_product_id=identity.get("project_product") or instance.project_product_id,
            module_id=identity.get("module") or instance.module_id,
            url=effective_url,
            method=effective_method,
            protocol_type=effective_protocol_type,
            body_type=effective_body_type,
            exclude_id=instance.id,
        )
        return cls.update_validated(
            instance,
            model_values,
            config,
            operator_id=operator_id,
            record_config=record_config,
        )

    @staticmethod
    def _validate_definition(
            *,
            project_product_id: int,
            module_id: int,
            url: str | None,
            method,
            protocol_type: str,
            body_type: str,
            exclude_id: int | None = None,
    ) -> None:
        url_error = ApiInfoConfigService.validate_url_path(url, protocol_type=protocol_type)
        if url_error:
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=(url_error,))
        duplicate = ApiInfoConfigService.find_duplicate_api_config(
            project_product_id=project_product_id,
            module_id=module_id,
            url=url,
            method=method,
            protocol_type=protocol_type,
            body_type=body_type,
            exclude_id=exclude_id,
        )
        if duplicate:
            raise AutoApiError(
                API_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED,
                value=(duplicate.id,),
            )

    @classmethod
    @transaction.atomic
    def delete_definition(cls, api_info_id: int) -> None:
        instance = ApiInfo.objects.select_for_update().filter(id=api_info_id).first()
        if instance is None:
            raise AutoApiError(API_VERSION_API_INFO_NOT_FOUND, value=(api_info_id,))
        instance.delete()

    @classmethod
    @transaction.atomic
    def create(cls, payload: dict, *, source: str = "internal") -> ApiInfo:
        ProductModuleService.validate_crud_binding(ApiInfo, payload)
        try:
            instance = save_model(ApiInfo, payload)
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        ApiConfigDiffService.record_instance_change(
            instance,
            action="create",
            source=source,
        )
        return instance

    @classmethod
    @transaction.atomic
    def create_validated(
            cls,
            validated_data: dict,
            runtime_config: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
    ) -> ApiInfo:
        payload = dict(validated_data)
        if operator_id is not None:
            payload["update_user"] = operator_id
        ProductModuleService.validate_crud_binding(ApiInfo, payload)
        try:
            instance = save_model(ApiInfo, payload)
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        ApiInfoRuntimeService.apply_payload(instance, runtime_config)
        ApiInfoRuntimeService.sync_protocol_config(instance)
        if record_config:
            ApiConfigDiffService.record_instance_change(instance, action="create", source="internal")
        return instance

    @classmethod
    @transaction.atomic
    def update_validated(
            cls,
            instance: ApiInfo,
            validated_data: dict,
            runtime_config: dict,
            *,
            operator_id: int | None = None,
            record_config: bool = True,
    ) -> ApiInfo:
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(instance).snapshot
        current_runtime = ApiInfoRuntimeService.resolve_runtime(instance.id, allow_draft=True)
        payload = dict(validated_data)
        if operator_id is not None:
            payload["update_user"] = operator_id
        ProductModuleService.validate_crud_binding(ApiInfo, payload, instance=instance)
        try:
            instance = save_model(ApiInfo, payload, instance=instance, partial=True)
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
        merged_config = ApiInfoRuntimeService.merge_editing_payload(
            current_runtime,
            runtime_config,
        )
        ApiInfoRuntimeService.apply_payload(instance, merged_config)
        ApiInfoRuntimeService.sync_protocol_config(instance)
        instance = cls._assert_persisted_update(
            instance,
            validated_data=payload,
            runtime_config=runtime_config,
            expected_runtime=merged_config,
        )
        if record_config:
            ApiConfigDiffService.record_instance_change(
                instance,
                action="update",
                before_snapshot=before_snapshot,
                source="internal",
            )
        return instance

    @classmethod
    def _assert_persisted_update(
            cls,
            instance: ApiInfo,
            *,
            validated_data: dict,
            runtime_config: dict,
            expected_runtime: dict,
    ) -> ApiInfo:
        persisted = ApiInfo.objects.get(pk=instance.pk)
        persisted_runtime = ApiInfoRuntimeService.current_payload(persisted)
        errors: dict[str, list[str]] = {}

        for field_name in runtime_config:
            if field_name not in API_INFO_CONFIG_FIELDS:
                continue
            if persisted_runtime.get(field_name) != expected_runtime.get(field_name):
                errors[field_name] = ['接口配置保存后回读不一致']

        for field_name, expected in validated_data.items():
            if field_name == 'id' or field_name in runtime_config:
                continue
            try:
                model_field = ApiInfo._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            actual = getattr(persisted, model_field.attname)
            if model_field.is_relation:
                expected = getattr(expected, 'pk', expected)
            if actual != expected:
                errors[field_name] = ['接口基础信息保存后回读不一致']

        if errors:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(errors,))
        return persisted
