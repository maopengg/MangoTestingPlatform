from django.db import transaction

from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_FIELDS_LIST_REQUIRED,
    DATA_FACTORY_FIELD_FIELD_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryEntity, DataFactoryField
from src.apps.data_factory.schemas.configuration import validate_data_factory_generator_config
from src.apps.data_factory.services.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.runtime_cache import DataFactoryRuntimeCache
from src.apps.data_factory.services.type_cast import DataFactoryTypeCast
from src.common.database import ModelMutationValidationError, model_payload, save_model


# -*- coding: utf-8 -*-


class DataFactoryFieldService:
    """字段规则保存和预览的统一业务入口。"""

    @classmethod
    @transaction.atomic
    def save_schema_fields(
            cls,
            entity: DataFactoryEntity,
            columns: list,
            replace: bool = True,
            update_user_id: int | None = None,
    ) -> list:
        saved_fields = []
        field_names = []
        for index, column in enumerate(columns):
            recommend = column.get("recommend", {}) or {}
            instance = DataFactoryField.objects.filter(entity=entity, name=column.get("name")).first()
            field_data = {
                **column,
                "entity": entity.id,
                "generator_type": (
                    column["generator_type"]
                    if "generator_type" in column
                    else instance.generator_type if instance else recommend.get("generator_type", 1)
                ),
                "generator_config": (
                    column["generator_config"]
                    if "generator_config" in column
                    else instance.generator_config if instance else recommend.get("generator_config", {})
                ),
                "sort": column.get("sort", index),
            }
            if update_user_id:
                field_data["update_user"] = update_user_id
            if not field_data.get("name"):
                raise DataFactoryError(DATA_FACTORY_FIELD_FIELD_REQUIRED)
            cls.normalize_field_data(field_data)
            field_names.append(field_data["name"])
            try:
                saved = save_model(
                    DataFactoryField,
                    field_data,
                    instance=instance,
                    partial=bool(instance),
                )
            except ModelMutationValidationError as error:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
            saved_fields.append(model_payload(saved))

        if replace:
            DataFactoryField.objects.filter(entity=entity).exclude(name__in=field_names).delete()
        return saved_fields

    @classmethod
    def preview_values(
            cls,
            fields: list[dict],
            context: dict | None = None,
            entity_id: int | None = None,
            test_env: int | None = None,
    ) -> dict:
        if not isinstance(fields, list):
            raise DataFactoryError(DATA_FACTORY_FIELDS_LIST_REQUIRED)

        context = context or {}
        test_data = None
        if entity_id:
            entity = DataFactoryEntity.objects.select_related("project_product").get(id=entity_id)
            test_data = DataFactoryRuntimeCache.build_test_data(entity.project_product_id, test_env)

        payload = {}
        rows = []
        for raw_field_data in fields:
            field_data = dict(raw_field_data)
            try:
                field_data["generator_config"] = field_data.get("generator_config") or {}
                cls.normalize_field_data(field_data)
                field = DataFactoryField(
                    name=field_data.get("name"),
                    label=field_data.get("label") or field_data.get("name"),
                    db_type=field_data.get("db_type") or field_data.get("platform_type") or "string",
                    platform_type=field_data.get("platform_type") or "string",
                    nullable=field_data.get("nullable", True),
                    primary_key=field_data.get("primary_key", False),
                    autoincrement=field_data.get("autoincrement", False),
                    max_length=field_data.get("max_length"),
                    enum_values=field_data.get("enum_values") or [],
                    generator_type=field_data.get("generator_type", DataFactoryGeneratorTypeEnum.FIXED.value),
                    generator_config=field_data.get("generator_config") or {},
                    sort=field_data.get("sort", 0),
                )
                if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                    rows.append({
                        "name": field.name,
                        "value": field.generator_config.get("reason") or "数据库生成",
                        "valid": True,
                        "message": "跳过字段",
                    })
                    continue
                if field.generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
                    dependency_preview = cls.preview_dependency_field(field, context)
                    if dependency_preview is not None:
                        rows.append(dependency_preview)
                        continue

                value = DataFactoryValueGenerator.generate(field, payload, context)
                value = DataFactoryValueGenerator.replace_value(value, test_data)
                value = DataFactoryTypeCast.cast(value, field.platform_type)
                DataFactoryValueGenerator.validate(field, value)
                payload[field.name] = value
                rows.append({
                    "name": field.name,
                    "value": DataFactoryTypeCast.to_jsonable(value),
                    "valid": True,
                    "message": "",
                })
            except Exception as error:
                rows.append({
                    "name": field_data.get("name"),
                    "value": None,
                    "valid": False,
                    "message": str(error),
                })

        return {
            "payload": DataFactoryTypeCast.to_jsonable(payload),
            "fields": rows,
        }

    @staticmethod
    def normalize_field_data(field_data: dict):
        generator_type = field_data.get("generator_type")
        generator_config = field_data.get("generator_config") or {}
        enum_values = field_data.get("enum_values") or []
        config_keys = {
            DataFactoryGeneratorTypeEnum.RANDOM_STRING.value: ["prefix", "length"],
            DataFactoryGeneratorTypeEnum.RANDOM_INTEGER.value: ["min", "max"],
            DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value: ["min", "max", "precision"],
            DataFactoryGeneratorTypeEnum.RELATIVE_TIME.value: ["days", "hours", "minutes"],
            DataFactoryGeneratorTypeEnum.UUID.value: ["dash"],
        }
        if generator_type == DataFactoryGeneratorTypeEnum.FIXED.value:
            field_data["generator_config"] = {"value": generator_config.get("value")}
        elif generator_type in config_keys:
            field_data["generator_config"] = {
                key: generator_config[key]
                for key in config_keys[generator_type]
                if key in generator_config and generator_config[key] not in [None, ""]
            }
        elif generator_type == DataFactoryGeneratorTypeEnum.NOW.value:
            field_data["generator_config"] = {}
        elif generator_type == DataFactoryGeneratorTypeEnum.ENUM.value:
            values = generator_config.get("values") or enum_values
            if not values:
                field_data["generator_type"] = DataFactoryGeneratorTypeEnum.FIXED.value
                field_data["generator_config"] = {"value": ""}
        elif generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            field_data["generator_config"] = {"value": generator_config.get("value") or ""}
        elif generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            field_data["generator_config"] = validate_data_factory_generator_config(
                DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                DataFactoryFieldService.normalize_dependency_config(generator_config),
                allow_dependency_template=False,
            )

    @staticmethod
    def normalize_dependency_config(generator_config: dict) -> dict:
        config = dict(generator_config or {})
        normalized = {
            "dependency_entity_id": config.get("dependency_entity_id"),
            "field": config.get("field") or "id",
        }
        return {key: value for key, value in normalized.items() if value not in [None, ""]}

    @staticmethod
    def preview_dependency_field(field: DataFactoryField, context: dict):
        config = field.generator_config or {}
        alias = config.get("alias")
        target_field = config.get("field", "id")
        if alias and alias in context:
            return None
        if alias:
            value = f"${{{{{alias}.{target_field}}}}}"
            message = "依赖字段，当前复用上下文占位值"
            valid = True
        elif config.get("dependency_entity_id"):
            value = f"${{{{依赖实体:{config.get('dependency_entity_id')}.{target_field}}}}}"
            message = "依赖实体字段，状态模板/API中需选择依赖状态模板"
            valid = True
        else:
            value = None
            message = "依赖字段未配置依赖实体"
            valid = False
        return {
            "name": field.name,
            "value": value,
            "valid": valid,
            "message": message,
        }
