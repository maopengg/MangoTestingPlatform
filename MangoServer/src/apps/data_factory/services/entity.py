from django.db import transaction
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryEntityStatusChangeSourceEnum,
    DataFactoryTemplateConfigStatusEnum,
)
from src.apps.data_factory.enums import DataFactoryOperationTypeEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_REQUIRED,
    DATA_FACTORY_ENTITY_MODULE_REQUIRED,
    DATA_FACTORY_ENTITY_PROJECT_PRODUCT_MODULE_INVALID,
    DATA_FACTORY_ENTITY_DATABASE_REQUIRED,
    DATA_FACTORY_ENTITY_TEST_ENVIRONMENT_INVALID,
    DATA_FACTORY_ENTITY_MINIMUM_REQUIRED,
    DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID,
    DATA_FACTORY_MODULE_ENTITY_INVALID,
    DATA_FACTORY_CONFIG_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryEntity,
    DataFactoryEntityStatusLog,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.data_factory.services.field import DataFactoryFieldService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.models import ProductModule
from src.common.database import ModelMutationValidationError, model_payload, save_model


# -*- coding: utf-8 -*-


class DataFactoryEntityService:
    """工厂实体创建编排的统一业务入口。"""

    @staticmethod
    @transaction.atomic
    def create(payload: dict, *, update_user_id: int | None = None) -> dict:
        data = dict(payload)
        if update_user_id is not None:
            data["update_user"] = update_user_id
        DataFactoryEntityService.validate_mutation(data)
        data.update({
            "create_type": DataFactoryOperationTypeEnum.SQL.value,
            "delete_type": DataFactoryOperationTypeEnum.SQL.value,
            "status": 0,
            "status_change_source": DataFactoryEntityStatusChangeSourceEnum.DATA_SYNC.value,
            "status_change_reason_code": "created_pending_schema_validation",
            "status_change_reason": "实体创建后等待表结构与字段规则校验",
        })
        try:
            return model_payload(save_model(DataFactoryEntity, data))
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error

    @classmethod
    @transaction.atomic
    def update(
            cls,
            entity_id: int,
            payload: dict,
            *,
            update_user_id: int | None = None,
    ) -> dict:
        entity = DataFactoryEntity.objects.select_for_update().get(id=entity_id)
        data = dict(payload)
        data.setdefault("id", entity_id)
        if update_user_id is not None:
            data["update_user"] = update_user_id
        cls.validate_mutation(data, instance=entity)
        target_status = data.pop("status", entity.status)
        try:
            entity = save_model(DataFactoryEntity, data, instance=entity, partial=True)
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
        if target_status != entity.status:
            result = cls.change_status(
                entity_id=entity.id,
                status=target_status,
                source=DataFactoryEntityStatusChangeSourceEnum.PAGE_MANUAL.value,
                reason_code=f"manual_{'enabled' if target_status == 1 else 'disabled'}",
                reason=f"页面手动{'启用' if target_status == 1 else '停用'}实体",
                operator_id=update_user_id,
                restore_invalidated_templates=target_status == 1,
            )
            entity = result["entity"]
        return model_payload(entity)

    @staticmethod
    def validate_mutation(data: dict, instance: DataFactoryEntity | None = None) -> None:
        datasource_alias_id = data.get(
            "datasource_alias",
            instance.datasource_alias_id if instance else None,
        )
        project_product_id = data.get(
            "project_product",
            instance.project_product_id if instance else None,
        )
        module_id = data.get("module", instance.module_id if instance else None)
        table_name = data.get("table_name", instance.table_name if instance else None)
        if not datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_DATABASE_REQUIRED)
        if not module_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_MODULE_REQUIRED)
        module = ProductModule.objects.filter(id=module_id).first()
        if project_product_id and module and module.project_product_id != int(project_product_id):
            raise DataFactoryError(DATA_FACTORY_ENTITY_PROJECT_PRODUCT_MODULE_INVALID)
        if not table_name:
            raise DataFactoryError(DATA_FACTORY_ENTITY_REQUIRED)
        duplicate = DataFactoryEntity.objects.filter(
            project_product_id=project_product_id,
            datasource_alias_id=datasource_alias_id,
            table_name=table_name,
            schema_name=data.get("schema_name", instance.schema_name if instance else ''),
        )
        if instance:
            duplicate = duplicate.exclude(id=instance.id)
        if duplicate.exists():
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(table_name,))

    @classmethod
    @transaction.atomic
    def change_status(
            cls,
            entity_id: int,
            status: int,
            source: int,
            reason_code: str,
            reason: str,
            operator_id: int | None = None,
            source_record_type: str | None = None,
            source_record_id: int | None = None,
            context: dict | None = None,
            invalidate_templates: bool = False,
            restore_invalidated_templates: bool = False,
    ) -> dict:
        if status not in [StatusEnum.FAIL.value, StatusEnum.SUCCESS.value]:
            raise DataFactoryError(DATA_FACTORY_PROJECT_PRODUCT_ENTITY_INVALID)
        if source not in DataFactoryEntityStatusChangeSourceEnum.obj():
            raise DataFactoryError(DATA_FACTORY_MODULE_ENTITY_INVALID)

        activation_validation = None
        if status == StatusEnum.SUCCESS.value:
            # 页面、API 和 MCP 的启用操作必须共用同一套真实表结构校验。
            from src.apps.data_factory.services.schema_monitor import DataFactorySchemaMonitorService
            activation_validation = DataFactorySchemaMonitorService.validate_entity_activation(entity_id)

        entity = DataFactoryEntity.objects.select_for_update().get(id=entity_id)
        from_status = entity.status
        if from_status == status:
            restoration = {"restored_template_ids": [], "failed_templates": []}
            if status == StatusEnum.SUCCESS.value and restore_invalidated_templates:
                from src.apps.data_factory.services.template import DataFactoryTemplateService
                restoration = DataFactoryTemplateService.restore_invalidated_templates(entity.id)
            return {
                "entity": entity,
                "changed": False,
                "status_log": None,
                "invalidated_template_count": 0,
                "restored_template_count": len(restoration["restored_template_ids"]),
                "failed_template_count": len(restoration["failed_templates"]),
                "failed_templates": restoration["failed_templates"],
                "activation_validation": activation_validation,
            }

        status_context = dict(context or {})
        invalidated_template_ids = []
        restored_template_ids = []
        if status == StatusEnum.FAIL.value and invalidate_templates:
            invalidated_templates = list(
                DataFactoryTemplate.objects.filter(
                    id__in=cls.related_template_ids(entity.id),
                ).values("id", "status")
            )
            invalidated_template_ids = sorted(item["id"] for item in invalidated_templates)
            if invalidated_template_ids:
                DataFactoryTemplate.objects.filter(id__in=invalidated_template_ids).update(
                    status=StatusEnum.FAIL.value,
                    config_status=DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value,
                    update_time=timezone.now(),
                )
                status_context["invalidated_template_ids"] = invalidated_template_ids
                status_context["invalidated_templates"] = invalidated_templates

        changed_at = timezone.now()
        entity.status = status
        entity.status_change_source = source
        entity.status_change_reason_code = reason_code
        entity.status_change_reason = reason
        entity.status_changed_at = changed_at
        entity.status_changed_by_id = operator_id
        entity.status_change_reference_type = source_record_type
        entity.status_change_reference_id = source_record_id
        if operator_id is not None:
            entity.update_user_id = operator_id
        entity.save(update_fields=[
            "status",
            "status_change_source",
            "status_change_reason_code",
            "status_change_reason",
            "status_changed_at",
            "status_changed_by",
            "status_change_reference_type",
            "status_change_reference_id",
            "update_user",
            "update_time",
        ])
        status_log = DataFactoryEntityStatusLog.objects.create(
            entity=entity,
            from_status=from_status,
            to_status=status,
            source=source,
            reason_code=reason_code,
            reason=reason,
            operator_id=operator_id,
            source_record_type=source_record_type,
            source_record_id=source_record_id,
            context=status_context,
        )
        failed_templates = []
        if status == StatusEnum.SUCCESS.value and restore_invalidated_templates:
            from src.apps.data_factory.services.template import DataFactoryTemplateService
            restoration = DataFactoryTemplateService.restore_invalidated_templates(entity.id)
            restored_template_ids = restoration["restored_template_ids"]
            failed_templates = restoration["failed_templates"]
            if restored_template_ids or failed_templates:
                status_log.context = {
                    **status_log.context,
                    "restored_template_ids": restored_template_ids,
                    "failed_templates": failed_templates,
                }
                status_log.save(update_fields=["context"])
        return {
            "entity": entity,
            "changed": True,
            "status_log": status_log,
            "invalidated_template_count": len(invalidated_template_ids),
            "restored_template_count": len(restored_template_ids),
            "failed_template_count": len(failed_templates),
            "failed_templates": failed_templates,
            "activation_validation": activation_validation,
        }

    @staticmethod
    def related_template_ids(entity_id: int) -> set[int]:
        affected_template_ids = set(
            DataFactoryTemplate.objects.filter(entity_id=entity_id).values_list("id", flat=True)
        )
        frontier = set(affected_template_ids)
        while frontier:
            parent_ids = set(
                DataFactoryTemplateItem.objects.filter(
                    child_template_id__in=frontier,
                ).values_list("template_id", flat=True)
            ) - affected_template_ids
            affected_template_ids.update(parent_ids)
            frontier = parent_ids
        return affected_template_ids

    @staticmethod
    def unavailable_error_values(entity: DataFactoryEntity) -> tuple[str, str, str, str]:
        source_name = DataFactoryEntityStatusChangeSourceEnum.get_value(
            getattr(entity, "status_change_source", DataFactoryEntityStatusChangeSourceEnum.UNKNOWN.value),
        ) or '历史来源未知'
        reason = getattr(entity, "status_change_reason", None) or '历史数据未记录停用原因'
        status_changed_at = getattr(entity, "status_changed_at", None)
        if status_changed_at:
            display_time = (
                timezone.localtime(status_changed_at)
                if timezone.is_aware(status_changed_at)
                else status_changed_at
            )
            changed_at = display_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            changed_at = '未知'
        return entity.name, source_name, reason, changed_at

    @classmethod
    def batch_generate(
            cls,
            project_product_id: int,
            module_id: int,
            datasource_alias_id: int,
            test_env: int,
            tables: list[dict],
            sync_fields: bool = True,
            skip_exists: bool = True,
    ) -> dict:
        if not project_product_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_REQUIRED)
        if not module_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_MODULE_REQUIRED)
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            raise DataFactoryError(DATA_FACTORY_ENTITY_PROJECT_PRODUCT_MODULE_INVALID)
        if not datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_ENTITY_DATABASE_REQUIRED)
        if is_missing_value(test_env):
            raise DataFactoryError(DATA_FACTORY_ENTITY_TEST_ENVIRONMENT_INVALID)
        if not isinstance(tables, list) or not tables:
            raise DataFactoryError(DATA_FACTORY_ENTITY_MINIMUM_REQUIRED)

        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id,
            project_product_id,
            test_env,
        )
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        database = DatasourceTargetService.for_metadata(binding)
        result_items = []
        success = skipped = failed = 0

        for table in tables:
            schema_name = table.get('schema_name', binding.schema_name)
            database = DatasourceTargetService.for_metadata(binding, schema_name=schema_name)
            table_name = table.get("table_name") or table.get("name")
            entity_name = table.get("name") or table.get("table_comment") or table_name
            if not table_name or not entity_name:
                failed += 1
                result_items.append(
                    cls._result_item(table_name, entity_name, "failed", None, 0, "表名和实体名称不能为空"))
                continue

            discovered_schema = None
            if database.db_type == DataSourceTypeEnum.POSTGRESQL.value and not schema_name:
                try:
                    discovered_schema = DataFactoryDiscover.get_table_schema(database, table_name)
                    schema_name = discovered_schema['schema_name']
                except Exception as error:
                    failed += 1
                    result_items.append(cls._result_item(table_name, entity_name, "failed", None, 0, str(error)))
                    continue

            duplicated = DataFactoryEntity.objects.filter(
                project_product_id=project_product_id,
                datasource_alias_id=datasource_alias_id,
                table_name=table_name,
                schema_name=schema_name,
            ).first()
            if duplicated:
                if skip_exists:
                    skipped += 1
                    result_items.append(cls._result_item(
                        table_name, duplicated.name, "skipped", duplicated.id, 0, "当前逻辑数据库下已存在实体"
                    ))
                else:
                    failed += 1
                    result_items.append(cls._result_item(
                        table_name, entity_name, "failed", duplicated.id, 0, "当前逻辑数据库下已存在实体"
                    ))
                continue

            try:
                schema = discovered_schema or DataFactoryDiscover.get_table_schema(database, table_name)
                unique_key = ""
                for index in schema.get("indexes") or []:
                    column_names = index.get("column_names") or []
                    if index.get("unique") and len(column_names) == 1:
                        unique_key = column_names[0]
                        break

                with transaction.atomic():
                    entity = DataFactoryEntity.objects.create(
                        project_product_id=project_product_id,
                        module_id=module_id,
                        datasource_alias_id=datasource_alias_id,
                        name=entity_name,
                        table_name=table_name,
                        schema_name=schema_name,
                        primary_key=(schema.get("primary_keys") or ["id"])[0],
                        unique_key=unique_key,
                        cleanup_order=100,
                        status=StatusEnum.FAIL.value,
                        status_change_source=DataFactoryEntityStatusChangeSourceEnum.DATA_SYNC.value,
                        status_change_reason_code="created_pending_schema_validation",
                        status_change_reason="实体创建后等待表结构与字段规则校验",
                    )
                    field_count = 0
                    if sync_fields:
                        field_count = len(DataFactoryFieldService.save_schema_fields(
                            entity,
                            schema.get("columns") or [],
                            replace=True,
                        ))
                    cls.change_status(
                        entity_id=entity.id,
                        status=StatusEnum.SUCCESS.value,
                        source=DataFactoryEntityStatusChangeSourceEnum.DATA_SYNC.value,
                        reason_code="schema_synced_and_validated",
                        reason="表结构同步完成且已通过启用校验",
                    )
                success += 1
                result_items.append(cls._result_item(
                    table_name, entity.name, "success", entity.id, field_count, "生成成功"
                ))
            except Exception as error:
                failed += 1
                result_items.append(cls._result_item(
                    table_name, entity_name, "failed", None, 0, str(error)
                ))

        return {
            "success": success,
            "skipped": skipped,
            "failed": failed,
            "items": result_items,
        }

    @staticmethod
    def _result_item(table_name, name, status, entity_id, field_count, message) -> dict:
        return {
            "table_name": table_name,
            "name": name,
            "status": status,
            "entity_id": entity_id,
            "field_count": field_count,
            "message": message,
        }
