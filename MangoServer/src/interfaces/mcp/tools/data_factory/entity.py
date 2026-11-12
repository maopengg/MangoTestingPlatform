from __future__ import annotations

from typing import Any

from django.db import transaction
from django.forms import model_to_dict
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryEntityStatusChangeSourceEnum,
    DataFactoryOperationTypeEnum,
)
from src.apps.data_factory.models import DataFactoryEntity
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.schema.discover import DataFactoryDiscover
from src.apps.data_factory.services.assets.entity import DataFactoryEntityService
from src.apps.data_factory.services.assets.field import DataFactoryFieldService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import paginate_queryset
from .helpers import (
    MangoServerError,
    fail,
    ok,
)


def _entity_status_metadata(entity: DataFactoryEntity) -> dict:
    changed_by = getattr(entity, "status_changed_by", None)
    return {
        "status": entity.status,
        "status_name": StatusEnum.get_value(entity.status),
        "status_change_source": entity.status_change_source,
        "status_change_source_name": DataFactoryEntityStatusChangeSourceEnum.get_value(
            entity.status_change_source,
        ),
        "status_change_reason_code": entity.status_change_reason_code,
        "status_change_reason": entity.status_change_reason,
        "status_changed_at": (
            entity.status_changed_at.strftime("%Y-%m-%d %H:%M:%S")
            if entity.status_changed_at else None
        ),
        "status_changed_by": (
            {
                "id": changed_by.id,
                "name": getattr(changed_by, "name", None),
                "username": getattr(changed_by, "username", None),
            }
            if changed_by else None
        ),
        "status_change_reference": (
            {
                "type": entity.status_change_reference_type,
                "id": entity.status_change_reference_id,
            }
            if entity.status_change_reference_type or entity.status_change_reference_id else None
        ),
    }


def register_entity_tools(mcp):
    @mcp.tool()
    def list_data_factory_entities(
            entity_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            datasource_alias_id: int | None = None,
            keyword: str | None = None,
            status_change_source: int | None = None,
            status_change_reason_code: str | None = None,
            enabled_only: bool = True,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询数据实体。"""
        queryset = DataFactoryQuerySelector.data_factory_entity().select_related(
            "project_product",
            "module",
            "datasource_alias",
            "status_changed_by",
        ).all()
        if entity_id is not None:
            queryset = queryset.filter(id=entity_id)
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if datasource_alias_id is not None:
            queryset = queryset.filter(datasource_alias_id=datasource_alias_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword) | queryset.filter(table_name__contains=keyword)
        if status_change_source is not None:
            queryset = queryset.filter(status_change_source=status_change_source)
        if status_change_reason_code:
            queryset = queryset.filter(status_change_reason_code=status_change_reason_code)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "table_name": item.table_name,
                        "schema_name": item.schema_name,
                        "primary_key": item.primary_key,
                        "unique_key": item.unique_key,
                        "project_product_id": item.project_product_id,
                        "module_id": item.module_id,
                        "datasource_alias_id": item.datasource_alias_id,
                        "datasource_alias_name": item.datasource_alias.name if item.datasource_alias_id else None,
                        "create_type": item.create_type,
                        "delete_type": DataFactoryOperationTypeEnum.SQL.value,
                        "cleanup_order": item.cleanup_order,
                        **_entity_status_metadata(item),
                    }
                    for item in queryset
                ],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_data_factory_entity_detail(entity_id: int) -> dict:
        """查询数据实体详情及字段规则。"""
        entity = DataFactoryQuerySelector.data_factory_entity().select_related(
            "project_product",
            "module",
            "datasource_alias",
            "status_changed_by",
        ).get(id=entity_id)
        fields = [model_to_dict(item) for item in
                  DataFactoryQuerySelector.data_factory_field().filter(entity_id=entity_id).order_by("sort", "id")]
        entity_data = model_to_dict(entity)
        entity_data["delete_type"] = DataFactoryOperationTypeEnum.SQL.value
        entity_data.update(_entity_status_metadata(entity))
        return ok({"entity": entity_data, "fields": fields})

    @mcp.tool()
    def list_data_factory_entity_status_logs(
            entity_id: int,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询数据实体状态变更审计，包括手动、MCP、结构巡检和系统修复来源。"""
        queryset = DataFactoryQuerySelector.data_factory_entity_status_log().select_related("operator").filter(
            entity_id=entity_id,
        ).order_by("-id")
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size)
        items = []
        for item in queryset:
            items.append({
                "id": item.id,
                "entity_id": item.entity_id,
                "from_status": item.from_status,
                "from_status_name": StatusEnum.get_value(item.from_status),
                "to_status": item.to_status,
                "to_status_name": StatusEnum.get_value(item.to_status),
                "source": item.source,
                "source_name": DataFactoryEntityStatusChangeSourceEnum.get_value(item.source),
                "reason_code": item.reason_code,
                "reason": item.reason,
                "operator": (
                    {
                        "id": item.operator.id,
                        "name": getattr(item.operator, "name", None),
                        "username": getattr(item.operator, "username", None),
                    }
                    if item.operator_id else None
                ),
                "source_record_type": item.source_record_type,
                "source_record_id": item.source_record_id,
                "context": item.context,
                "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return ok({
            "items": items,
            "count": count,
            "page": page,
            "page_size": page_size,
        })

    @mcp.tool()
    def create_data_factory_entity(
            project_product_id: int,
            module_id: int,
            datasource_alias_id: int,
            name: str,
            table_name: str,
            primary_key: str = "id",
            unique_key: str | None = None,
            delete_type: int = 2,
            cleanup_order: int = 100,
            description: str | None = None,
            status: int = StatusEnum.SUCCESS.value,
            test_env: int | None = None,
            sync_fields: bool = False,
            fields: list[dict] | None = None,
            replace_fields: bool = True,
            schema_name: str = '',
    ) -> dict:
        """创建数据实体。

        当前数据工厂只支持 SQL 创建和 SQL 清理，因此 create_type、delete_type 均固定为 SQL。
        delete_type 是兼容历史调用的保留参数，传入其他值也会按 SQL 保存。

        默认只创建实体定义。需要同时生成字段规则时：
        1. 推荐传 sync_fields=True 和 test_env，MCP 会按表结构同步字段规则；
        2. 或传 fields 手工保存字段规则；
        3. 已有实体可调用 batch_save_data_factory_fields 维护字段规则。

        fields 项格式与 batch_save_data_factory_fields 一致，常用字段包括：
        name、label、db_type、platform_type、nullable、primary_key、autoincrement、
        max_length、enum_values、generator_type、generator_config、sort。
        """
        if not TestCenterQuerySelector.product_module().filter(id=module_id,
                                                               project_product_id=project_product_id).exists():
            return fail("模块不属于当前项目/产品", "DATA_FACTORY_MODULE_MISMATCH")
        if fields is not None and not isinstance(fields, list):
            return fail("fields 必须是列表", "DATA_FACTORY_FIELDS_INVALID")
        if sync_fields and not fields and is_missing_value(test_env):
            return fail("sync_fields=True 时必须传 test_env，用于解析逻辑数据库对应的测试环境",
                        "DATA_FACTORY_TEST_ENV_REQUIRED")

        with transaction.atomic():
            data = DataFactoryEntityService.create(
                {
                    "project_product": project_product_id,
                    "module": module_id,
                    "datasource_alias": datasource_alias_id,
                    "name": name,
                    "description": description,
                    "table_name": table_name,
                    "schema_name": schema_name,
                    "primary_key": primary_key,
                    "unique_key": unique_key,
                    "create_type": DataFactoryOperationTypeEnum.SQL.value,
                    "delete_type": DataFactoryOperationTypeEnum.SQL.value,
                    "cleanup_order": cleanup_order,
                    "status": StatusEnum.FAIL.value,
                },
                update_user_id=mcp_current_user_id(),
            )
            entity = DataFactoryQuerySelector.data_factory_entity().get(id=data["id"])
            saved_fields = []
            field_sync_source = "none"
            if fields:
                saved_fields = DataFactoryFieldService.save_schema_fields(entity, fields, replace_fields)
                field_sync_source = "manual"
            elif sync_fields:
                binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
                    datasource_alias_id, project_product_id, test_env,
                )
                DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
                schema = DataFactoryDiscover.get_table_schema(
                    DatasourceTargetService.resolve(binding, schema_name=schema_name), table_name)
                saved_fields = DataFactoryFieldService.save_schema_fields(
                    entity,
                    schema.get("columns") or [],
                    replace=True,
                )
                field_sync_source = "table_schema"

            if status == StatusEnum.SUCCESS.value:
                status_result = DataFactoryEntityService.change_status(
                    entity_id=entity.id,
                    status=StatusEnum.SUCCESS.value,
                    source=DataFactoryEntityStatusChangeSourceEnum.MCP.value,
                    reason_code="mcp_enabled_after_validation",
                    reason="MCP 创建实体并通过表结构校验后启用",
                    operator_id=mcp_current_user_id(),
                    source_record_type="mcp_tool",
                )
                data.update(_entity_status_metadata(status_result["entity"]))

        return ok(
            {
                "entity_id": data["id"],
                **data,
                "fields_synced": bool(saved_fields),
                "field_sync_source": field_sync_source,
                "field_count": len(saved_fields),
                "fields": saved_fields,
            },
            "数据实体创建成功",
        )

    @mcp.tool()
    def update_data_factory_entity(
            entity_id: int,
            project_product_id: int | None = None,
            module_id: int | None = None,
            name: str | None = None,
            description: str | None = None,
            primary_key: str | None = None,
            unique_key: str | None = None,
            cleanup_order: int | None = None,
            status: int | None = None,
            schema_name: str | None = None,
    ) -> dict:
        """更新已有数据实体配置。

        project_product_id、module_id 用于迁移实体归属；不传则保留原归属。
        模块必须是目标项目/产品下的末级模块。
        当前删除方式固定为 SQL，更新任意实体时都会同步纠正历史删除方式配置。
        cleanup_order 数值越小越先清理，存在引用关系时应先配置子表、再配置主表。
        表结构修复场景中，只能在 get_data_factory_table_schema 与平台字段规则
        重新校验一致后才能传 status=1。工具按系统设置中的“数据模型校验环境”执行校验；
        未选择校验环境时校验所有已绑定环境，并自动重新校验本次结构变更联动停用的
        直接模板和递归上游模板。
        校验通过且原本为启用状态的模板会自动恢复；校验失败或原本手动停用的模板保持停用。
        """
        payload: dict[str, Any] = {
            "id": entity_id,
            "delete_type": DataFactoryOperationTypeEnum.SQL.value,
        }
        for key, value in {
            "project_product": project_product_id,
            "module": module_id,
            "name": name,
            "description": description,
            "primary_key": primary_key,
            "unique_key": unique_key,
            "cleanup_order": cleanup_order,
            "schema_name": schema_name,
        }.items():
            if value is not None:
                payload[key] = value
        try:
            data = DataFactoryEntityService.update(
                entity_id,
                payload,
                update_user_id=mcp_current_user_id(),
            )
            if status is not None:
                action_name = "启用" if status == StatusEnum.SUCCESS.value else "停用"
                status_result = DataFactoryEntityService.change_status(
                    entity_id=entity_id,
                    status=status,
                    source=DataFactoryEntityStatusChangeSourceEnum.MCP.value,
                    reason_code=f"mcp_{'enabled' if status == StatusEnum.SUCCESS.value else 'disabled'}",
                    reason=f"MCP 手动{action_name}实体",
                    operator_id=mcp_current_user_id(),
                    source_record_type="mcp_tool",
                    restore_invalidated_templates=status == StatusEnum.SUCCESS.value,
                )
                data.update(_entity_status_metadata(status_result["entity"]))
                data["template_revalidation"] = {
                    "restored_count": status_result.get("restored_template_count", 0),
                    "failed_count": status_result.get("failed_template_count", 0),
                    "failed_templates": status_result.get("failed_templates", []),
                }
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok({"entity_id": entity_id, **data}, "数据实体更新成功")

    @mcp.tool()
    def batch_generate_data_factory_entities(
            project_product_id: int,
            module_id: int,
            datasource_alias_id: int,
            test_env: int,
            tables: list[dict],
            sync_fields: bool = True,
            skip_exists: bool = True,
    ) -> dict:
        """根据表结构批量生成数据实体和字段规则。"""
        result = DataFactoryEntityService.batch_generate(
            project_product_id=project_product_id,
            module_id=module_id,
            datasource_alias_id=datasource_alias_id,
            test_env=test_env,
            tables=tables,
            sync_fields=sync_fields,
            skip_exists=skip_exists,
        )
        return ok(result, "数据实体批量生成完成")
