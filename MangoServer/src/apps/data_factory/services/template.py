from copy import deepcopy

from django.db import transaction
from django.utils import timezone
from mangotools.enums import StatusEnum
from pydantic import ValidationError

from src.apps.data_factory.enums import DataFactoryTemplateConfigStatusEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CONFIG_INVALID,
    DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED,
    DATA_FACTORY_FIELD_INVALID,
    DATA_FACTORY_MODULE_ENTITY_INVALID,
    DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID,
    DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID,
    DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID,
    DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryEntity,
    DataFactoryEntityStatusLog,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.apps.data_factory.schemas.configuration import (
    DataFactoryFieldOverrideRules,
    DataFactoryOutputConfig,
    DataFactoryPostInsertUpdates,
)
from src.apps.data_factory.services.preview import DataFactoryPreviewService
from src.apps.system.services.system_config import SystemConfigService
from src.apps.test_center.models import ProductModule
from src.common.database import ModelMutationValidationError, model_payload, save_model


# -*- coding: utf-8 -*-


class DataFactoryTemplateService:
    """场景模板状态与配置完整性统一业务入口。"""

    @staticmethod
    def refresh_config_status(template: DataFactoryTemplate, test_env=None) -> int:
        try:
            result = DataFactoryPreviewService.preview_template(
                template_id=template.id,
                overrides=template.field_overrides or {},
                output_config=template.output_config,
                test_env=test_env,
                activation_validation=True,
            )
            config_status = (
                DataFactoryTemplateConfigStatusEnum.READY.value
                if result.get("configuration_valid", result.get("can_debug_run"))
                else DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
            )
        except Exception:
            config_status = DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
        if template.config_status != config_status:
            template.config_status = config_status
            template.save(update_fields=["config_status", "update_time"])
        return config_status

    @classmethod
    def activation_environments(cls, template: DataFactoryTemplate, test_env=None) -> list[int | None]:
        environments = set()
        bindings = template.entity.datasource_alias.datafactorydatasourcebinding_set.all()
        for binding in bindings:
            environment = binding.environment
            if environment is not None:
                environments.add(environment)
        configured_environments = SystemConfigService.get_data_factory_validation_environments()
        if configured_environments is not None:
            selected_environments = environments.intersection(configured_environments)
            return sorted(selected_environments) or configured_environments
        return sorted(environments) or [None]

    @staticmethod
    def configuration_snapshot(template: DataFactoryTemplate) -> dict:
        return {
            "entity_id": template.entity_id,
            "project_product_id": template.project_product_id,
            "field_overrides": deepcopy(template.field_overrides or {}),
            "output_config": deepcopy(template.output_config or []),
            "post_insert_updates": deepcopy(template.post_insert_updates or []),
            "items": list(template.items.order_by("sort", "id").values(
                "id", "child_template_id", "name", "sort", "field_overrides",
            )),
        }

    @staticmethod
    def mark_configuration_pending(template: DataFactoryTemplate) -> set[int]:
        affected = {template.id}
        frontier = {template.id}
        while frontier:
            frontier = set(DataFactoryTemplateItem.objects.filter(
                child_template_id__in=frontier,
            ).values_list("template_id", flat=True)) - affected
            affected.update(frontier)
        DataFactoryTemplate.objects.filter(id__in=affected).update(
            config_status=DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value,
            update_time=timezone.now(),
        )
        template.config_status = DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
        return affected

    @classmethod
    def finish_configuration_save(
            cls, template: DataFactoryTemplate, *, before: dict | None,
            previous_status: int, target_status: int, operator_id: int | None = None,
    ) -> DataFactoryTemplate:
        # 普通编辑不访问业务库；造数规则变化使当前模板和上游入口失去执行资格。
        if before is None or before != cls.configuration_snapshot(template):
            cls.mark_configuration_pending(template)
        if target_status != previous_status:
            return cls.set_status(template.id, target_status, update_user_id=operator_id)
        return template

    @classmethod
    def validate_activation(
            cls,
            template: DataFactoryTemplate,
            test_env=None,
            allow_disabled_template_ids: set[int] | None = None,
    ) -> dict:
        from src.apps.data_factory.services.runner import DataFactoryRunner

        DataFactoryRunner.require_template_entities_available(
            template,
            allow_disabled_template_ids=allow_disabled_template_ids or {template.id},
        )
        checked_environments = []
        failures = []
        for environment in cls.activation_environments(template, test_env):
            try:
                result = DataFactoryPreviewService.preview_template(
                    template_id=template.id,
                    overrides=template.field_overrides or {},
                    output_config=template.output_config,
                    test_env=environment,
                    activation_validation=True,
                )
                if not result.get("configuration_valid", result.get("can_debug_run")):
                    invalid_update = next(
                        (
                            item for item in result.get("post_insert_updates") or []
                            if not item.get("valid", False)
                        ),
                        None,
                    )
                    if invalid_update:
                        failures.append(
                            f"环境 {environment}：插入后回写配置无效：{invalid_update.get('message') or '请检查节点与字段配置'}"
                        )
                        continue
                    missing = result.get("all_missing_fields") or DataFactoryRunner.collect_preview_missing_fields(
                        result.get("template") or {},
                        result.get("entity") or {},
                        result.get("missing_fields") or [],
                        result.get("dependencies") or [],
                    )
                    fields = "、".join(
                        f"{item.get('path') or item.get('template_name') or template.name} / "
                        f"{item.get('field') or '未知字段'}"
                        for item in missing[:5]
                    )
                    failures.append(f"环境 {environment}：缺少有效字段值 {fields or '或配置不完整'}")
                else:
                    checked_environments.append(environment)
            except Exception as error:
                failures.append(f"环境 {environment}：{error}")
        if failures:
            if template.config_status != DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value:
                template.config_status = DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value
                template.save(update_fields=["config_status", "update_time"])
            raise DataFactoryError(DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED, value=(template.name, failures[0]))
        if template.config_status != DataFactoryTemplateConfigStatusEnum.READY.value:
            template.config_status = DataFactoryTemplateConfigStatusEnum.READY.value
            template.save(update_fields=["config_status", "update_time"])
        return {"template_id": template.id, "checked_environments": checked_environments}

    @classmethod
    def restore_invalidated_templates(cls, entity_id: int) -> dict:
        disable_log = DataFactoryEntityStatusLog.objects.filter(
            entity_id=entity_id,
            to_status=StatusEnum.FAIL.value,
        ).exclude(context={}).order_by("-id").first()
        context = disable_log.context if disable_log else {}
        records = context.get("invalidated_templates") or []
        previous_status_by_id = {
            int(item["id"]): item.get("status", StatusEnum.FAIL.value)
            for item in records
            if isinstance(item, dict) and item.get("id") is not None
        }
        template_ids = context.get("invalidated_template_ids") or list(previous_status_by_id)
        restored_template_ids = []
        failed_templates = []
        templates = DataFactoryTemplate.objects.select_related(
            "entity", "entity__datasource_alias",
        ).filter(id__in=template_ids).order_by("id")
        invalidated_id_set = {template.id for template in templates}
        for template in templates:
            # 新巡检记录只恢复原本启用的模板；旧记录未改模板 status，保持兼容。
            should_enable = (
                previous_status_by_id.get(template.id) == StatusEnum.SUCCESS.value
                if records
                else template.status == StatusEnum.SUCCESS.value
            )
            if not should_enable:
                continue
            try:
                cls.validate_activation(
                    template,
                    allow_disabled_template_ids=invalidated_id_set,
                )
                if template.status != StatusEnum.SUCCESS.value:
                    template.status = StatusEnum.SUCCESS.value
                    template.save(update_fields=["status", "update_time"])
                restored_template_ids.append(template.id)
            except Exception as error:
                failed_templates.append({"template_id": template.id, "reason": str(error)})
        return {
            "restored_template_ids": restored_template_ids,
            "failed_templates": failed_templates,
        }

    @staticmethod
    def set_status(
            template_id: int,
            status: int,
            update_user_id: int | None = None,
            test_env=None,
    ) -> DataFactoryTemplate:
        template = DataFactoryTemplate.objects.select_related(
            "entity", "entity__datasource_alias",
        ).get(id=template_id)
        if status == StatusEnum.SUCCESS.value:
            DataFactoryTemplateService.validate_activation(template, test_env)
        template.status = status
        if update_user_id is not None:
            template.update_user_id = update_user_id
        template.save(update_fields=["status", "update_user", "update_time"])
        return template


class DataFactoryTemplateMutationService:
    @classmethod
    @transaction.atomic
    def create(cls, payload: dict, *, operator_id: int | None = None) -> dict:
        data, items = cls._validated_payload(payload, operator_id=operator_id)
        target_status = data.pop("status", StatusEnum.SUCCESS.value)
        data["status"] = StatusEnum.FAIL.value
        data.pop("config_status", None)
        try:
            instance = save_model(DataFactoryTemplate, data)
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
        cls._sync_after_save(instance, items)
        instance = DataFactoryTemplateService.finish_configuration_save(
            instance, before=None, previous_status=StatusEnum.FAIL.value,
            target_status=target_status, operator_id=operator_id,
        )
        return model_payload(instance)

    @classmethod
    @transaction.atomic
    def update(cls, template_id: int, payload: dict, *, operator_id: int | None = None) -> dict:
        instance = DataFactoryTemplate.objects.select_for_update().get(id=template_id)
        before = DataFactoryTemplateService.configuration_snapshot(instance)
        previous_status = instance.status
        data, items = cls._validated_payload(payload, instance=instance, operator_id=operator_id)
        target_status = data.pop("status", previous_status)
        data.pop("config_status", None)
        try:
            instance = save_model(DataFactoryTemplate, data, instance=instance, partial=True)
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
        cls._sync_after_save(instance, items)
        instance = DataFactoryTemplateService.finish_configuration_save(
            instance, before=before, previous_status=previous_status,
            target_status=target_status, operator_id=operator_id,
        )
        return model_payload(instance)

    @staticmethod
    @transaction.atomic
    def delete(template_id: int) -> None:
        from src.apps.data_factory.services.template_deletion import DataFactoryTemplateDeletionService

        DataFactoryTemplateDeletionService.delete_many([template_id])

    @classmethod
    def _validated_payload(
            cls,
            payload: dict,
            *,
            instance: DataFactoryTemplate | None = None,
            operator_id: int | None = None,
    ) -> tuple[dict, list | None]:
        data = dict(payload)
        data.pop("id", None)
        items = data.pop("items", None)
        project_product_id = data.get("project_product", instance.project_product_id if instance else None)
        module_id = data.get("module", instance.module_id if instance else None)
        entity_id = data.get("entity", instance.entity_id if instance else None)
        name = data.get("name", instance.name if instance else None)
        if not module_id:
            raise DataFactoryError(DATA_FACTORY_SCENARIO_MODULE_TEMPLATE_BINDING_INVALID)
        module = ProductModule.objects.get(id=module_id)
        entity = DataFactoryEntity.objects.get(id=entity_id)
        if module.project_product_id != project_product_id:
            raise DataFactoryError(DATA_FACTORY_PROJECT_PRODUCT_MODULE_INVALID)
        if entity.project_product_id != project_product_id:
            raise DataFactoryError(DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID)
        if entity.module_id and entity.module_id != module_id:
            raise DataFactoryError(DATA_FACTORY_MODULE_ENTITY_INVALID)
        duplicated = DataFactoryTemplate.objects.filter(entity_id=entity_id, name=name)
        if instance:
            duplicated = duplicated.exclude(id=instance.id)
        if duplicated.exists():
            raise DataFactoryError(DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED, value=(name,))
        try:
            if "field_overrides" in data:
                data["field_overrides"] = DataFactoryFieldOverrideRules.model_validate(
                    data.get("field_overrides") or {},
                ).model_dump()
            if "output_config" in data:
                data["output_config"] = DataFactoryOutputConfig.model_validate(
                    data.get("output_config") or [],
                ).model_dump()
            if "post_insert_updates" in data:
                data["post_insert_updates"] = DataFactoryPostInsertUpdates.model_validate(
                    data.get("post_insert_updates") or [],
                ).model_dump()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_FIELD_INVALID, value=(error,)) from error
        if operator_id is not None:
            data["update_user"] = operator_id
        return data, items

    @classmethod
    def _sync_after_save(cls, instance: DataFactoryTemplate, items: list | None) -> None:
        if instance.is_default:
            DataFactoryTemplate.objects.filter(
                entity_id=instance.entity_id,
                is_default=True,
            ).exclude(id=instance.id).update(is_default=False)
        if items is not None:
            cls._sync_items(instance, items)

    @staticmethod
    def _sync_items(instance: DataFactoryTemplate, items: list) -> None:
        keep_ids = []
        for index, raw_item in enumerate(items or []):
            data = dict(raw_item)
            item_id = data.pop("id", None)
            child_id = data.get("child_template")
            child = DataFactoryTemplate.objects.get(id=getattr(child_id, "id", child_id))
            if child.id == instance.id or child.project_product_id != instance.project_product_id:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("关联模板无效",))
            data["child_template"] = child.id
            data["template"] = instance.id
            data.setdefault("sort", index)
            data.setdefault("name", child.name)
            data["field_overrides"] = DataFactoryFieldOverrideRules.model_validate(
                data.get("field_overrides") or {},
            ).model_dump()
            if instance.update_user_id:
                data.setdefault("update_user", instance.update_user_id)
            item = DataFactoryTemplateItem.objects.filter(id=item_id, template=instance).first() if item_id else None
            try:
                item = save_model(
                    DataFactoryTemplateItem,
                    data,
                    instance=item,
                    partial=item is not None,
                )
            except ModelMutationValidationError as error:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
            keep_ids.append(item.id)
        DataFactoryTemplateItem.objects.filter(template=instance).exclude(id__in=keep_ids).delete()
