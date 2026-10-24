# -*- coding: utf-8 -*-

from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.enums import DataFactoryTemplateUsageScopeEnum
from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID, DataFactoryError
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.schemas.configuration import validate_data_factory_scene_overrides
from src.common.database import ModelMutationValidationError, save_model


class DataFactoryCaseConfigService:
    """API/UI 用例数据工厂绑定配置的统一业务入口。"""

    @staticmethod
    def api_case_id(source_type: int, source_id: int) -> int | None:
        if source_type == DataFactoryCaseSourceTypeEnum.API_CASE.value:
            return source_id
        if source_type == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value:
            return ApiCaseDetailedParameter.objects.filter(id=source_id).values_list(
                "case_detailed__case_id",
                flat=True,
            ).first()
        return None

    @classmethod
    def create(
            cls,
            payload: dict,
            update_user_id: int | None = None,
            source: str = "page",
    ) -> DataFactoryCaseConfig:
        data = dict(payload)
        if update_user_id is not None:
            data["update_user"] = update_user_id

        def save(_=None):
            try:
                return save_model(DataFactoryCaseConfig, cls._normalize(data))
            except ModelMutationValidationError as error:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error

        case_id = cls.api_case_id(data.get("source_type"), data.get("source_id"))
        if case_id is not None:
            return ApiCaseAggregateMutationService.mutate(
                case_id,
                action="bind_data_factory",
                operation=save,
                operator_id=update_user_id,
                source=source,
                refresh_case_flow=False,
            )
        with transaction.atomic():
            return save()

    @classmethod
    def update(
            cls,
            config_id: int,
            payload: dict,
            update_user_id: int | None = None,
            source: str = "page",
    ) -> DataFactoryCaseConfig:
        config = DataFactoryCaseConfig.objects.get(id=config_id)
        data = dict(payload)
        if update_user_id is not None:
            data["update_user"] = update_user_id

        def save(_=None):
            locked_config = DataFactoryCaseConfig.objects.select_for_update().get(id=config_id)
            try:
                return save_model(
                    DataFactoryCaseConfig,
                    cls._normalize(data, locked_config),
                    instance=locked_config,
                    partial=True,
                )
            except ModelMutationValidationError as error:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error

        case_id = cls.api_case_id(config.source_type, config.source_id)
        if case_id is not None:
            return ApiCaseAggregateMutationService.mutate(
                case_id,
                action="update_data_factory",
                operation=save,
                operator_id=update_user_id,
                source=source,
                refresh_case_flow=False,
            )
        with transaction.atomic():
            return save()

    @classmethod
    @transaction.atomic
    def sort(
            cls,
            source_type: int,
            items: list[dict],
            update_user_id: int | None = None,
            source: str = "page",
    ) -> list[dict]:
        requested_updates = []
        for item in items:
            config_id = item.get("config_id") or item.get("id")
            sort = item.get("sort")
            if config_id is None or sort is None:
                continue
            requested_updates.append({"config_id": config_id, "sort": sort})

        configs = {
            config.id: config
            for config in DataFactoryCaseConfig.objects.filter(
                id__in=[item["config_id"] for item in requested_updates],
                source_type=source_type,
            )
        }
        updates_by_case: dict[int | None, list[dict]] = {}
        for item in requested_updates:
            config = configs.get(item["config_id"])
            if config is None:
                continue
            case_id = cls.api_case_id(config.source_type, config.source_id)
            updates_by_case.setdefault(case_id, []).append(item)

        def apply_updates(case_updates: list[dict]):
            for update in case_updates:
                values = {"sort": update["sort"], "update_time": timezone.now()}
                if update_user_id is not None:
                    values["update_user_id"] = update_user_id
                DataFactoryCaseConfig.objects.select_for_update().filter(
                    id=update["config_id"],
                    source_type=source_type,
                ).update(**values)

        for case_id, case_updates in updates_by_case.items():
            if case_id is None:
                apply_updates(case_updates)
                continue
            ApiCaseAggregateMutationService.mutate(
                case_id,
                action="sort_data_factory",
                operation=lambda _, values=case_updates: apply_updates(values),
                operator_id=update_user_id,
                source=source,
                refresh_case_flow=False,
            )
        return [item for values in updates_by_case.values() for item in values]

    @staticmethod
    def _normalize(data: dict, instance: DataFactoryCaseConfig | None = None) -> dict:
        normalized = dict(data)
        if normalized.get("cleanup_strategy") == "":
            normalized["cleanup_strategy"] = None
        if normalized.get("case") is not None and normalized.get("source_id") is None:
            normalized["source_id"] = normalized.pop("case")
        source_type = normalized.get("source_type", instance.source_type if instance else None)
        if source_type not in DataFactoryCaseSourceTypeEnum.obj():
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("用例来源类型不正确",))
        source_id = normalized.get("source_id", instance.source_id if instance else None)
        if not source_id:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("用例ID不能为空",))
        template_id = normalized.get("template", instance.template_id if instance else None)
        if template_id:
            from src.apps.data_factory.models import DataFactoryTemplate
            template = DataFactoryTemplate.objects.filter(id=template_id).first()
            if template and template.usage_scope == DataFactoryTemplateUsageScopeEnum.INTERNAL.value:
                raise DataFactoryError(
                    DATA_FACTORY_CONFIG_INVALID,
                    value=("仅场景内部引用用途的场景模板不能绑定到用例",),
                )
        overrides = normalized.get(
            "field_overrides",
            instance.field_overrides if instance else {},
        )
        try:
            normalized["field_overrides"] = validate_data_factory_scene_overrides(overrides or {})
        except (ValidationError, ValueError) as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(str(error),)) from error
        return normalized
