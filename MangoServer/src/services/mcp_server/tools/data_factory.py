from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from django.db import transaction
from django.forms import model_to_dict

from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.apps.auto_data_factory.models import (
    DataFactoryCaseConfig,
    DataFactoryDatasourceAlias,
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryField,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.apps.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.apps.auto_data_factory.service.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver, is_missing_value
from src.apps.auto_data_factory.service.discover import DataFactoryDiscover
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.apps.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasCRUD
from src.apps.auto_data_factory.views.datasource_binding import DataFactoryDatasourceBindingCRUD
from src.apps.auto_data_factory.views.entity import DataFactoryEntityCRUD, DataFactoryEntityViews
from src.apps.auto_data_factory.views.field import DataFactoryFieldCRUD, DataFactoryFieldViews
from src.apps.auto_data_factory.views.template import DataFactoryTemplateCRUD
from src.apps.auto_system.models import Database, ProductModule
from src.common.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryOperationTypeEnum,
)
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import MangoServerError
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


def _selected_test_env(user_id: int | None = None, test_env: int | None = None) -> int | None:
    if test_env is not None:
        return test_env
    try:
        user = current_user(user_id)
    except Exception:
        return None
    return user.selected_environment


def _database_from_args(
    database_id: int | None = None,
    datasource_alias_id: int | None = None,
    test_object_id: int | None = None,
    project_product_id: int | None = None,
    test_env: int | None = None,
) -> Database:
    if datasource_alias_id is not None:
        if not is_missing_value(test_env) and not is_missing_value(project_product_id):
            return DataFactoryDatasourceResolver.resolve_alias_by_env(datasource_alias_id, project_product_id, test_env)
        return DataFactoryDatasourceResolver.resolve_alias(datasource_alias_id, test_object_id)
    if database_id is None:
        raise ValueError("database_id 或 datasource_alias_id 必须提供一个")
    return Database.objects.get(id=database_id)


def _template_cache_prefix(template: DataFactoryTemplate, name: str | None = None) -> str:
    return name or template.name


def _cache_keys_for_template(template: DataFactoryTemplate, name: str | None = None) -> list[str]:
    prefix = _template_cache_prefix(template, name)
    keys = [
        f"${{{{{prefix}}}}}",
        f"${{{{{prefix}.__execution_id}}}}",
        f"${{{{{prefix}.__execution_no}}}}",
    ]
    for field_name in DataFactoryField.objects.filter(entity_id=template.entity_id).order_by("sort", "id").values_list("name", flat=True):
        keys.append(f"${{{{{prefix}.{field_name}}}}}")
    for scene_item in template.items.select_related("child_template", "child_template__entity").order_by("sort", "id"):
        item_prefix = f"{prefix}.{scene_item.name or scene_item.child_template.name}"
        keys.append(f"${{{{{item_prefix}}}}}")
        for field_name in DataFactoryField.objects.filter(entity_id=scene_item.child_template.entity_id).order_by("sort", "id").values_list("name", flat=True):
            keys.append(f"${{{{{item_prefix}.{field_name}}}}}")
    return keys


def _data_factory_result_with_cache_keys(result: dict, template: DataFactoryTemplate, name: str | None = None) -> dict:
    data = dict(result or {})
    data["cache_prefix"] = _template_cache_prefix(template, name)
    data["cache_keys"] = _cache_keys_for_template(template, name)
    return data


def _normalize_output_config(output_config: list | None) -> list:
    """Accept MCP-friendly shorthand and convert it to DataFactoryOutputConfigItem shape."""
    if not output_config:
        return []
    normalized = []
    for item in output_config:
        if isinstance(item, str):
            value = item.strip()
            if value:
                normalized.append({"field": value, "key": value})
            continue
        if not isinstance(item, dict):
            continue
        field = item.get("field") or item.get("name")
        key = item.get("key") or field
        if field and key:
            normalized.append({"field": field, "key": key})
    return normalized


def _data_factory_template_run_target(
    template_id: int,
    overrides: dict | None = None,
    context: dict | None = None,
    test_object_id: int | None = None,
    test_env: int | None = None,
    user_id: int | None = None,
) -> str:
    payload = {
        "template_id": template_id,
        "overrides": overrides or {},
        "context": context or {},
        "test_object_id": test_object_id,
        "test_env": test_env,
        "user_id": user_id,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{template_id}:{digest}"


def _template_summary(item: DataFactoryTemplate, name: str | None = None) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "project_product_id": item.project_product_id,
        "module_id": item.module_id,
        "entity_id": item.entity_id,
        "entity_name": item.entity.name if item.entity_id else None,
        "field_overrides": item.field_overrides,
        "output_config": item.output_config,
        "cleanup_strategy": item.cleanup_strategy,
        "is_default": item.is_default,
        "usage_scope": item.usage_scope,
        "status": item.status,
        "items": [
            _template_item_summary(scene_item)
            for scene_item in item.items.select_related("child_template", "child_template__entity").order_by("sort", "id")
        ],
        "cache_prefix": _template_cache_prefix(item, name),
        "cache_keys": _cache_keys_for_template(item, name),
    }


def _template_item_summary(item: DataFactoryTemplateItem) -> dict:
    return {
        "id": item.id,
        "child_template": item.child_template_id,
        "child_template_name": item.child_template.name if item.child_template_id else None,
        "child_entity_id": item.child_template.entity_id if item.child_template_id else None,
        "child_entity_name": item.child_template.entity.name if item.child_template_id and item.child_template.entity_id else None,
        "name": item.name,
        "sort": item.sort,
        "field_overrides": item.field_overrides,
    }


def _case_config_summary(config: DataFactoryCaseConfig) -> dict:
    template = config.template
    return {
        "id": config.id,
        "config_id": config.id,
        "source_type": config.source_type,
        "source_id": config.source_id,
        "template_id": config.template_id,
        "template_name": template.name,
        "name": config.name,
        "stage": config.stage,
        "sort": config.sort,
        "field_overrides": config.field_overrides,
        "cleanup_strategy": config.cleanup_strategy,
        "status": config.status,
        "cache_prefix": _template_cache_prefix(template, config.name),
        "cache_keys": _cache_keys_for_template(template, config.name),
    }


def _validate_case_source(source_type: int, source_id: int) -> str | None:
    if source_type == DataFactoryCaseSourceTypeEnum.API_CASE.value:
        if not ApiCase.objects.filter(id=source_id).exists():
            return "API case 不存在"
    elif source_type == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value:
        if not ApiCaseDetailedParameter.objects.filter(id=source_id).exists():
            return "API 接口场景不存在"
    elif source_type == DataFactoryCaseSourceTypeEnum.UI_CASE.value:
        # UI case support is intentionally only existence-light here to keep this module decoupled.
        return None
    else:
        return "source_type 不正确，只支持 1(API用例)、2(UI用例)、3(API接口场景)"
    return None


def _execution_summary(item: DataFactoryExecution) -> dict:
    return {
        "id": item.id,
        "execution_no": item.execution_no,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "template_id": item.template_id,
        "template_name": item.template.name if item.template_id else None,
        "project_product_id": item.project_product_id,
        "module_id": item.module_id,
        "stage": item.stage,
        "status": item.status,
        "cleanup_status": item.cleanup_status,
        "error_message": item.error_message,
        "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
        "cleanup_time": item.cleanup_time.strftime("%Y-%m-%d %H:%M:%S") if item.cleanup_time else None,
    }


def _execution_detail(execution_id: int) -> dict:
    execution = DataFactoryExecution.objects.select_related("template", "project_product", "module").get(id=execution_id)
    items = []
    for item in DataFactoryExecutionItem.objects.select_related("template", "database").filter(execution_id=execution_id).order_by("cleanup_order", "id"):
        items.append(
            {
                "id": item.id,
                "template_id": item.template_id,
                "template_name": item.template.name if item.template_id else None,
                "database_id": item.database_id,
                "database_name": item.database.name if item.database_id else None,
                "alias": item.alias,
                "primary_value": item.primary_value,
                "data": item.data,
                "cleanup_strategy": item.cleanup_strategy,
                "cleanup_order": item.cleanup_order,
                "cleanup_status": item.cleanup_status,
                "cleanup_error": item.cleanup_error,
            }
        )
    cache_keys = []
    if execution.template_id:
        cache_keys = _cache_keys_for_template(execution.template)
    return {"execution": _execution_summary(execution), "items": items, "context": execution.context, "cache_keys": cache_keys}


def register_data_factory_tools(mcp):
    @mcp.tool()
    def list_data_factory_datasource_aliases(
        project_product_id: int | None = None,
        keyword: str | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询数据工厂逻辑数据源。"""
        queryset = DataFactoryDatasourceAlias.objects.select_related("project_product", "project_product__project").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword) | queryset.filter(code__contains=keyword)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "code": item.code,
                        "db_type": item.db_type,
                        "description": item.description,
                        "project_product_id": item.project_product_id,
                        "project_product_name": item.project_product.name,
                        "status": item.status,
                    }
                    for item in queryset.order_by("-id")
                ]
            }
        )

    @mcp.tool()
    def create_data_factory_datasource_alias(
        project_product_id: int,
        name: str,
        code: str,
        db_type: int = 0,
        description: str | None = None,
        status: int = StatusEnum.SUCCESS.value,
    ) -> dict:
        """创建数据工厂逻辑数据源。"""
        data = DataFactoryDatasourceAliasCRUD.inside_post(
            {
                "project_product": project_product_id,
                "name": name,
                "code": code,
                "db_type": db_type,
                "description": description,
                "status": status,
            }
        )
        return ok({"datasource_alias_id": data["id"], **data}, "逻辑数据源创建成功")

    @mcp.tool()
    def list_data_factory_datasource_bindings(
        datasource_alias_id: int | None = None,
        test_object_id: int | None = None,
        project_product_id: int | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询逻辑数据源与测试环境真实数据库的绑定。"""
        queryset = DataFactoryDatasourceBinding.objects.select_related(
            "datasource_alias",
            "test_object",
            "database",
        )
        if datasource_alias_id is not None:
            queryset = queryset.filter(datasource_alias_id=datasource_alias_id)
        if test_object_id is not None:
            queryset = queryset.filter(test_object_id=test_object_id)
        if project_product_id is not None:
            queryset = queryset.filter(datasource_alias__project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "datasource_alias_id": item.datasource_alias_id,
                        "datasource_alias_name": item.datasource_alias.name,
                        "datasource_alias_code": item.datasource_alias.code,
                        "test_object_id": item.test_object_id,
                        "test_object_title": item.test_object.name if hasattr(item.test_object, "name") else str(item.test_object),
                        "database_id": item.database_id,
                        "database_name": item.database.name,
                        "description": item.description,
                        "status": item.status,
                    }
                    for item in queryset.order_by("-id")
                ]
            }
        )

    @mcp.tool()
    def create_data_factory_datasource_binding(
        datasource_alias_id: int,
        test_object_id: int,
        database_id: int,
        description: str | None = None,
        status: int = StatusEnum.SUCCESS.value,
    ) -> dict:
        """创建逻辑数据源到真实数据库的环境绑定。"""
        data = DataFactoryDatasourceBindingCRUD.inside_post(
            {
                "datasource_alias": datasource_alias_id,
                "test_object": test_object_id,
                "database": database_id,
                "description": description,
                "status": status,
            }
        )
        return ok({"binding_id": data["id"], **data}, "数据源绑定创建成功")

    @mcp.tool()
    def test_data_factory_datasource_connection(
        database_id: int | None = None,
        datasource_alias_id: int | None = None,
        test_object_id: int | None = None,
        project_product_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """测试数据工厂数据源连接。"""
        env = _selected_test_env(user_id, test_env)
        database = _database_from_args(database_id, datasource_alias_id, test_object_id, project_product_id, env)
        return ok(DataFactoryDatasource.test_connection(database), "数据源连接测试完成")

    @mcp.tool()
    def list_data_factory_database_tables(
        database_id: int | None = None,
        datasource_alias_id: int | None = None,
        test_object_id: int | None = None,
        project_product_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """查询数据工厂数据源中的表列表。"""
        env = _selected_test_env(user_id, test_env)
        database = _database_from_args(database_id, datasource_alias_id, test_object_id, project_product_id, env)
        return ok({"items": DataFactoryDiscover.get_tables(database)})

    @mcp.tool()
    def get_data_factory_table_schema(
        table_name: str,
        database_id: int | None = None,
        datasource_alias_id: int | None = None,
        test_object_id: int | None = None,
        project_product_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """查询数据工厂数据源中的单表字段 schema。"""
        env = _selected_test_env(user_id, test_env)
        database = _database_from_args(database_id, datasource_alias_id, test_object_id, project_product_id, env)
        return ok(DataFactoryDiscover.get_table_schema(database, table_name))

    @mcp.tool()
    def list_data_factory_entities(
        entity_id: int | None = None,
        project_product_id: int | None = None,
        module_id: int | None = None,
        datasource_alias_id: int | None = None,
        keyword: str | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询数据工厂实体。"""
        queryset = DataFactoryEntity.objects.select_related("project_product", "module", "datasource_alias").all()
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
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "table_name": item.table_name,
                        "primary_key": item.primary_key,
                        "unique_key": item.unique_key,
                        "project_product_id": item.project_product_id,
                        "module_id": item.module_id,
                        "datasource_alias_id": item.datasource_alias_id,
                        "datasource_alias_name": item.datasource_alias.name if item.datasource_alias_id else None,
                        "create_type": item.create_type,
                        "delete_type": item.delete_type,
                        "cleanup_order": item.cleanup_order,
                        "status": item.status,
                    }
                    for item in queryset.order_by("-id")
                ]
            }
        )

    @mcp.tool()
    def get_data_factory_entity_detail(entity_id: int) -> dict:
        """查询数据工厂实体详情及字段规则。"""
        entity = DataFactoryEntity.objects.select_related("project_product", "module", "datasource_alias").get(id=entity_id)
        fields = [model_to_dict(item) for item in DataFactoryField.objects.filter(entity_id=entity_id).order_by("sort", "id")]
        return ok({"entity": model_to_dict(entity), "fields": fields})

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
    ) -> dict:
        """创建数据工厂实体。

        当前数据工厂调试/执行只支持 SQL 创建方式，因此实体创建方式固定为 SQL，不需要也不能传 create_type。

        默认只创建实体定义。需要同时生成字段规则时：
        1. 推荐传 sync_fields=True 和 test_env，MCP 会按表结构同步字段规则；
        2. 或传 fields 手工保存字段规则；
        3. 已有实体可调用 batch_save_data_factory_fields 维护字段规则。

        fields 项格式与 batch_save_data_factory_fields 一致，常用字段包括：
        name、label、db_type、platform_type、nullable、primary_key、autoincrement、
        max_length、enum_values、generator_type、generator_config、sort。
        """
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            return fail("模块不属于当前项目/产品", "DATA_FACTORY_MODULE_MISMATCH")
        if fields is not None and not isinstance(fields, list):
            return fail("fields 必须是列表", "DATA_FACTORY_FIELDS_INVALID")
        if sync_fields and not fields and is_missing_value(test_env):
            return fail("sync_fields=True 时必须传 test_env，用于解析逻辑数据源对应的测试环境", "DATA_FACTORY_TEST_ENV_REQUIRED")

        with transaction.atomic():
            data = DataFactoryEntityCRUD.inside_post(
                {
                    "project_product": project_product_id,
                    "module": module_id,
                    "datasource_alias": datasource_alias_id,
                    "name": name,
                    "description": description,
                    "table_name": table_name,
                    "primary_key": primary_key,
                    "unique_key": unique_key,
                    "create_type": DataFactoryOperationTypeEnum.SQL.value,
                    "delete_type": delete_type,
                    "cleanup_order": cleanup_order,
                    "status": status,
                }
            )
            entity = DataFactoryEntity.objects.get(id=data["id"])
            saved_fields = []
            field_sync_source = "none"
            if fields:
                saved_fields = DataFactoryFieldViews.save_schema_fields(entity, fields, replace_fields)
                field_sync_source = "manual"
            elif sync_fields:
                database = _database_from_args(
                    datasource_alias_id=datasource_alias_id,
                    project_product_id=project_product_id,
                    test_env=test_env,
                )
                schema = DataFactoryDiscover.get_table_schema(database, table_name)
                saved_fields = DataFactoryFieldViews.save_schema_fields(entity, schema.get("columns") or [], replace=True)
                field_sync_source = "table_schema"

        return ok(
            {
                "entity_id": data["id"],
                **data,
                "fields_synced": bool(saved_fields),
                "field_sync_source": field_sync_source,
                "field_count": len(saved_fields),
                "fields": saved_fields,
            },
            "数据工厂实体创建成功",
        )

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
        """根据表结构批量生成数据工厂实体和字段规则。"""
        if not tables:
            return fail("tables 不能为空", "DATA_FACTORY_TABLES_EMPTY")
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            return fail("模块不属于当前项目/产品", "DATA_FACTORY_MODULE_MISMATCH")
        # Reuse the view helper logic by constructing the same core loop is avoided here; call the service-level view method is request-bound.
        request_like = {
            "project_product": project_product_id,
            "module": module_id,
            "datasource_alias": datasource_alias_id,
            "test_env": test_env,
            "tables": tables,
            "sync_fields": sync_fields,
            "skip_exists": skip_exists,
        }
        # Minimal request shim for the existing view method.
        class _Request:
            data = request_like

        response = DataFactoryEntityViews().batch_generate(_Request())  # type: ignore[arg-type]
        return ok(response.data.get("data"), "数据工厂实体批量生成完成")

    @mcp.tool()
    def list_data_factory_fields(entity_id: int, keyword: str | None = None) -> dict:
        """查询数据工厂实体字段规则。"""
        queryset = DataFactoryField.objects.filter(entity_id=entity_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        return ok({"items": [model_to_dict(item) for item in queryset.order_by("sort", "id")]})

    @mcp.tool()
    def batch_save_data_factory_fields(entity_id: int, fields: list[dict], replace: bool = False) -> dict:
        """批量保存数据工厂字段规则。

        字段规则是工厂实体生成数据的核心配置，不是状态模板 field_overrides。
        replace=True 会删除该实体下未出现在本次 fields 中的字段，请谨慎使用。

        fields 项常用字段：name、label、db_type、platform_type、nullable、primary_key、
        autoincrement、max_length、enum_values、generator_type、generator_config、sort。
        字符串类字段优先使用 generator_type=13 测试数据方法生成，
        可先调用 list_test_data_methods 查询可用方法和表达式示例。
        """
        entity = DataFactoryEntity.objects.get(id=entity_id)
        with transaction.atomic():
            saved = DataFactoryFieldViews.save_schema_fields(entity, fields, replace)
        return ok({"items": saved, "count": len(saved)}, "字段规则保存成功")

    @mcp.tool()
    def preview_data_factory_field_values(fields: list[dict], context: dict | None = None) -> dict:
        """预览字段规则生成值，不落库。

        generator_type=13 的 generator_config.value 支持 ${{方法名(...)}} 表达式；
        可用方法通过 list_test_data_methods 查询，也可用 evaluate_test_data_expression 试算。
        """
        class _Request:
            data = {"fields": fields, "context": context or {}}

        response = DataFactoryFieldViews().preview_values(_Request())  # type: ignore[arg-type]
        return ok(response.data.get("data"), "字段规则预览完成")

    @mcp.tool()
    def list_data_factory_templates(
        template_id: int | None = None,
        project_product_id: int | None = None,
        module_id: int | None = None,
        entity_id: int | None = None,
        keyword: str | None = None,
        usage_scope: int | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询数据工厂场景模板。

        usage_scope 用于区分模板可见范围：
        - 1 用例可直接选择：会出现在 API/UI case 的数据工厂选择列表，可直接绑定到用例执行。
        - 2 仅场景内部引用：不会出现在 case 选择列表，只用于被其他场景模板编排引用。
        不传 usage_scope 时返回全部用途。
        """
        queryset = DataFactoryTemplate.objects.select_related("entity", "module", "project_product").all()
        if template_id is not None:
            queryset = queryset.filter(id=template_id)
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if entity_id is not None:
            queryset = queryset.filter(entity_id=entity_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        if usage_scope is not None:
            queryset = queryset.filter(usage_scope=usage_scope)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        return ok({"items": [_template_summary(item) for item in queryset.order_by("-id")]})

    @mcp.tool()
    def get_data_factory_template_detail(template_id: int, name: str | None = None) -> dict:
        """查询数据工厂场景模板详情、实体、关联模板、字段和可用缓存变量。"""
        template = DataFactoryTemplate.objects.select_related("entity", "project_product", "module").get(id=template_id)
        fields = [model_to_dict(item) for item in DataFactoryField.objects.filter(entity_id=template.entity_id).order_by("sort", "id")]
        return ok(
            {
                "template": _template_summary(template, name),
                "entity": model_to_dict(template.entity),
                "fields": fields,
                "cache_prefix": _template_cache_prefix(template, name),
                "cache_keys": _cache_keys_for_template(template, name),
            }
        )

    @mcp.tool()
    def create_data_factory_template(
        project_product_id: int,
        module_id: int,
        entity_id: int,
        name: str,
        description: str | None = None,
        field_overrides: dict | None = None,
        output_config: list | None = None,
        items: list[dict] | None = None,
        cleanup_strategy: int = DataFactoryCleanupStrategyEnum.MANUAL.value,
        is_default: bool = False,
        usage_scope: int = 1,
        status: int = StatusEnum.SUCCESS.value,
        test_env: int | None = None,
    ) -> dict:
        """创建数据工厂场景模板。

        is_default=True 时设为该实体的默认模板，同实体其他默认模板会自动取消。
        usage_scope 场景用途，默认 1：
        - 1 用例可直接选择：用于完整业务对象入口，API/UI case 可直接选择执行。
        - 2 仅场景内部引用：用于底层子表/中间表/补充数据，只能被其他场景模板作为关联模板使用。
        items 用于配置关联模板，格式：
        [{"child_template": 20, "name": "流程分类绑定", "sort": 10, "field_overrides": {}}]
        关联模板清理策略继承场景模板。
        test_env 用于保存后刷新配置状态 config_status；不传时按页面逻辑使用空环境预览。
        字符串类字段覆盖优先使用 generator_type=13 测试数据方法；调用 list_test_data_methods 获取可用类型。
        """
        try:
            data = DataFactoryTemplateCRUD.inside_post(
                {
                    "project_product": project_product_id,
                    "module": module_id,
                    "entity": entity_id,
                    "name": name,
                    "description": description,
                    "field_overrides": field_overrides or {},
                    "output_config": _normalize_output_config(output_config),
                    "items": items or [],
                    "cleanup_strategy": cleanup_strategy,
                    "is_default": is_default,
                    "usage_scope": usage_scope,
                    "status": status,
                }
            )
            template = DataFactoryTemplate.objects.get(id=data["id"])
            DataFactoryTemplateCRUD.refresh_config_status(template, test_env)
            template.refresh_from_db()
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok(
            {
                "template_id": data["id"],
                **data,
                "config_status": template.config_status,
                "cache_keys": _cache_keys_for_template(template),
            },
            "场景模板创建成功",
        )

    @mcp.tool()
    def update_data_factory_template(
        template_id: int,
        project_product_id: int | None = None,
        module_id: int | None = None,
        entity_id: int | None = None,
        name: str | None = None,
        description: str | None = None,
        field_overrides: dict | None = None,
        output_config: list | None = None,
        items: list[dict] | None = None,
        cleanup_strategy: int | None = None,
        is_default: bool | None = None,
        usage_scope: int | None = None,
        status: int | None = None,
        test_env: int | None = None,
    ) -> dict:
        """更新数据工厂场景模板。

        is_default=True 时设为该实体的默认模板，同实体其他默认模板会自动取消。
        usage_scope 场景用途：
        - 1 用例可直接选择：API/UI case 可直接选择执行。
        - 2 仅场景内部引用：隐藏于 case 选择列表，只能被场景编排引用。
        items 不传则不修改关联模板；传入时以完整列表覆盖保存。
        关联模板清理策略继承场景模板。
        test_env 用于保存后刷新配置状态 config_status；页面 PUT /data-factory/template 也是这样处理。
        字符串类字段覆盖优先使用 generator_type=13 测试数据方法；调用 list_test_data_methods 获取可用类型。
        """
        payload: dict[str, Any] = {"id": template_id}
        for key, value in {
            "project_product": project_product_id,
            "module": module_id,
            "entity": entity_id,
            "name": name,
            "description": description,
            "field_overrides": field_overrides,
            "output_config": _normalize_output_config(output_config) if output_config is not None else None,
            "items": items,
            "cleanup_strategy": cleanup_strategy,
            "is_default": is_default,
            "usage_scope": usage_scope,
            "status": status,
        }.items():
            if value is not None:
                payload[key] = value
        try:
            data = DataFactoryTemplateCRUD.inside_put(template_id, payload)
            template = DataFactoryTemplate.objects.get(id=template_id)
            DataFactoryTemplateCRUD.refresh_config_status(template, test_env)
            template.refresh_from_db()
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok(
            {
                "template_id": template_id,
                **data,
                "config_status": template.config_status,
                "cache_keys": _cache_keys_for_template(template),
            },
            "场景模板更新成功",
        )

    @mcp.tool()
    def preview_data_factory_template(
        template_id: int,
        overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """预览数据工厂场景模板生成结果，不落库。"""
        template = DataFactoryTemplate.objects.get(id=template_id)
        env = _selected_test_env(user_id, test_env)
        result = DataFactoryRunner.preview_template(
            template_id=template_id,
            overrides=overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
        return ok(_data_factory_result_with_cache_keys(result, template), "模板预览完成")

    @mcp.tool()
    def preview_run_data_factory_template_impact(
        template_id: int,
        overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """预览场景模板将要生成的数据，并生成真实执行所需的二次确认 token。

        这是执行场景模板前的必经步骤。返回的 impact.preview_data 是即将落库的数据预览；
        用户确认后，再把 preview_token 和 confirm_text 原样传给 execute_data_factory_template。
        """
        template = DataFactoryTemplate.objects.get(id=template_id)
        env = _selected_test_env(user_id, test_env)
        preview = DataFactoryRunner.preview_template(
            template_id=template_id,
            overrides=overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
        preview_data = _data_factory_result_with_cache_keys(preview, template)
        target_id = _data_factory_template_run_target(template_id, overrides, context, test_object_id, env, user_id)
        confirm_text = f"RUN_DATA_FACTORY_TEMPLATE:{template_id}:{template.name}"
        impact = {
            "preview_data": preview_data,
            "template": preview_data.get("template"),
            "entity": preview_data.get("entity"),
            "database": preview_data.get("database"),
            "payload": preview_data.get("payload"),
            "output": preview_data.get("output"),
            "fields": preview_data.get("fields"),
            "missing_fields": preview_data.get("missing_fields"),
            "dependencies": preview_data.get("dependencies"),
            "dependency_tree": preview_data.get("dependency_tree"),
            "context": preview_data.get("context"),
            "cache_prefix": preview_data.get("cache_prefix"),
            "cache_keys": preview_data.get("cache_keys"),
            "can_execute": preview_data.get("can_debug_run"),
            "risk": "确认后会真实向数据源写入数据，并生成数据工厂执行记录；如场景模板存在关联模板或依赖实体，也会按配置创建数据。",
        }
        if not preview_data.get("can_debug_run"):
            return fail(
            "场景模板预览存在缺失字段或依赖不可执行，请先修正字段规则后再执行。",
                "DATA_FACTORY_TEMPLATE_PREVIEW_INVALID",
                impact,
            )
        return ok(
            create_dangerous_action_preview("run_data_factory_template", target_id, confirm_text, impact),
            "场景模板执行预览完成，请二次确认后执行",
        )

    @mcp.tool()
    def execute_data_factory_template(
        template_id: int,
        overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """真实执行数据工厂场景模板，会落库并生成执行记录。必须先调用 preview_run_data_factory_template_impact。"""
        env = _selected_test_env(user_id, test_env)
        target_id = _data_factory_template_run_target(template_id, overrides, context, test_object_id, env, user_id)
        confirm_error = validate_dangerous_action_confirmation(
            "run_data_factory_template",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        template = DataFactoryTemplate.objects.get(id=template_id)
        result = DataFactoryRunner.debug_run_template(
            template_id=template_id,
            overrides=overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
        return ok(_data_factory_result_with_cache_keys(result, template), "场景模板执行完成")

    @mcp.tool()
    def set_data_factory_template_status(template_id: int, status: Literal[0, 1]) -> dict:
        """启用或停用数据工厂场景模板。"""
        template = DataFactoryTemplate.objects.get(id=template_id)
        template.status = status
        template.save(update_fields=["status", "update_time"])
        return ok({"template_id": template.id, "status": template.status}, "状态模板状态更新成功")

    @mcp.tool()
    def preview_delete_data_factory_template_impact(template_id: int) -> dict:
        """预览删除数据工厂场景模板的影响，并生成二次确认 token。"""
        template = DataFactoryTemplate.objects.select_related("project_product", "module", "entity").get(id=template_id)
        case_configs = list(
            DataFactoryCaseConfig.objects.select_related("template", "template__entity")
            .filter(template_id=template_id)
            .order_by("source_type", "source_id", "sort", "id")[:50]
        )
        execution_queryset = DataFactoryExecution.objects.filter(template_id=template_id)
        execution_count = execution_queryset.count()
        recent_executions = [
            _execution_summary(item)
            for item in execution_queryset.select_related("template", "project_product", "module").order_by("-create_time")[:10]
        ]
        can_delete = len(case_configs) == 0
        impact = {
            "template": _template_summary(template),
            "entity": {
                "id": template.entity_id,
                "name": template.entity.name if template.entity_id else None,
                "table_name": template.entity.table_name if template.entity_id else None,
            },
            "is_default": template.is_default,
            "bound_case_config_count": DataFactoryCaseConfig.objects.filter(template_id=template_id).count(),
            "bound_case_configs_preview": [_case_config_summary(item) for item in case_configs],
            "execution_count": execution_count,
            "recent_executions": recent_executions,
            "can_delete": can_delete,
            "will_delete": "DataFactoryTemplate 场景模板记录",
            "delete_blockers": [] if can_delete else ["该状态模板已被 API/UI 用例或 API 场景绑定，数据库 PROTECT 会阻止删除。请先解绑或改用停用。"],
            "risk": "删除后无法再通过该模板创建测试数据；历史执行记录会保留，但 template 关联可能置空或无法继续按模板复用。",
            "safer_alternative": "优先使用 set_data_factory_template_status(status=0) 停用场景模板。",
        }
        confirm_text = f"DELETE_DATA_FACTORY_TEMPLATE:{template.id}:{template.name}"
        return ok(
            create_dangerous_action_preview("delete_data_factory_template", template.id, confirm_text, impact),
            "已生成场景模板删除影响预览",
        )

    @mcp.tool()
    def delete_data_factory_template(
        template_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """删除数据工厂场景模板。必须先调用 preview_delete_data_factory_template_impact，并传回 token 和确认文案。"""
        confirm_error = validate_dangerous_action_confirmation(
            "delete_data_factory_template",
            template_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        bound_count = DataFactoryCaseConfig.objects.filter(template_id=template_id).count()
        if bound_count:
            return fail(
                "场景模板已被用例绑定，不能删除。请先解绑，或使用 set_data_factory_template_status(status=0) 停用。",
                "DATA_FACTORY_TEMPLATE_DELETE_BLOCKED",
                {"template_id": template_id, "bound_case_config_count": bound_count},
            )
        try:
            DataFactoryTemplateCRUD.inside_delete(template_id)
        except Exception as exc:
            return fail(str(exc), "DATA_FACTORY_TEMPLATE_DELETE_FAILED")
        return ok({"template_id": template_id}, "数据工厂场景模板已删除")

    @mcp.tool()
    def list_data_factory_case_configs(source_type: int, source_id: int | None = None) -> dict:
        """查询 API/UI 用例或场景绑定的数据工厂配置。"""
        queryset = DataFactoryCaseConfig.objects.select_related("template", "template__entity").filter(source_type=source_type)
        if source_id is not None:
            queryset = queryset.filter(source_id=source_id)
        return ok({"items": [_case_config_summary(item) for item in queryset.order_by("sort", "id")]})

    @mcp.tool()
    def bind_data_factory_to_case_source(
        source_type: Literal[1, 2, 3],
        source_id: int,
        template_id: int,
        name: str | None = None,
        stage: int = 1,
        sort: int = 0,
        field_overrides: dict | None = None,
        cleanup_strategy: int | None = DataFactoryCleanupStrategyEnum.MANUAL.value,
        status: int = StatusEnum.SUCCESS.value,
        deduplicate: bool = True,
    ) -> dict:
        """给 API case、UI case 或 API 场景绑定数据工厂前置配置。"""
        source_error = _validate_case_source(source_type, source_id)
        if source_error:
            return fail(source_error, "INVALID_DATA_FACTORY_CASE_SOURCE")
        template = DataFactoryTemplate.objects.get(id=template_id)
        config_name = name or template.name
        queryset = DataFactoryCaseConfig.objects.filter(
            source_type=source_type,
            source_id=source_id,
            template_id=template_id,
            name=config_name,
        )
        if deduplicate and queryset.exists():
            config = queryset.order_by("id").first()
            return ok(_case_config_summary(config), "数据工厂前置配置已存在")
        config = DataFactoryCaseConfig.objects.create(
            source_type=source_type,
            source_id=source_id,
            template_id=template_id,
            name=config_name,
            stage=stage,
            sort=sort,
            field_overrides=field_overrides or {},
            cleanup_strategy=cleanup_strategy,
            status=status,
        )
        return ok(_case_config_summary(config), "数据工厂前置配置绑定成功")

    @mcp.tool()
    def update_data_factory_case_config(
        config_id: int,
        name: str | None = None,
        stage: int | None = None,
        sort: int | None = None,
        field_overrides: dict | None = None,
        cleanup_strategy: int | None = None,
        status: int | None = None,
    ) -> dict:
        """更新数据工厂用例绑定配置。"""
        config = DataFactoryCaseConfig.objects.select_related("template").get(id=config_id)
        for field, value in {
            "name": name,
            "stage": stage,
            "sort": sort,
            "field_overrides": field_overrides,
            "cleanup_strategy": cleanup_strategy,
            "status": status,
        }.items():
            if value is not None:
                setattr(config, field, value)
        config.save()
        return ok(_case_config_summary(config), "数据工厂绑定配置更新成功")

    @mcp.tool()
    def sort_data_factory_case_configs(source_type: int, items: list[dict]) -> dict:
        """调整数据工厂用例绑定配置顺序。items 格式为 [{config_id, sort}]。"""
        updated = []
        for item in items:
            config_id = item.get("config_id") or item.get("id")
            sort = item.get("sort")
            if config_id is None or sort is None:
                continue
            DataFactoryCaseConfig.objects.filter(id=config_id, source_type=source_type).update(sort=sort)
            updated.append({"config_id": config_id, "sort": sort})
        return ok({"items": updated}, "数据工厂绑定配置排序成功")

    @mcp.tool()
    def preview_data_factory_case_config(
        template_id: int,
        field_overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """预览数据工厂用例绑定配置，不落库。"""
        return preview_data_factory_template(
            template_id=template_id,
            overrides=field_overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=test_env,
            user_id=user_id,
        )

    @mcp.tool()
    def list_data_factory_executions(
        project_product_id: int | None = None,
        module_id: int | None = None,
        template_id: int | None = None,
        source_type: int | None = None,
        source_id: int | None = None,
        status: int | None = None,
        cleanup_status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """查询数据工厂执行记录。"""
        queryset = DataFactoryExecution.objects.select_related("template", "project_product", "module").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if template_id is not None:
            queryset = queryset.filter(template_id=template_id)
        if source_type is not None:
            queryset = queryset.filter(source_type=source_type)
        if source_id is not None:
            queryset = queryset.filter(source_id=source_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if cleanup_status is not None:
            queryset = queryset.filter(cleanup_status=cleanup_status)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        return ok(
            {
                "items": [_execution_summary(item) for item in queryset.order_by("-create_time")[offset : offset + page_size]],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_data_factory_execution_detail(execution_id: int) -> dict:
        """查询数据工厂执行详情、明细和上下文。"""
        return ok(_execution_detail(execution_id))

    @mcp.tool()
    def get_data_factory_execution_context(execution_id: int) -> dict:
        """查询数据工厂执行上下文。"""
        execution = DataFactoryExecution.objects.get(id=execution_id)
        return ok({"execution_id": execution.id, "execution_no": execution.execution_no, "context": execution.context})

    @mcp.tool()
    def preview_cleanup_data_factory_execution_impact(execution_id: int, force_cleanup: bool = False) -> dict:
        """预览清理某次数据工厂执行记录创建数据的影响，并生成二次确认 token。"""
        detail = _execution_detail(execution_id)
        items = detail["items"]
        pending_items = [
            item
            for item in items
            if force_cleanup or item.get("cleanup_status") != DataFactoryCleanupStatusEnum.SUCCESS.value
        ]
        impact = {
            "execution": detail["execution"],
            "will_cleanup_item_count": len(pending_items),
            "total_item_count": len(items),
            "items": [
                {
                    "id": item.get("id"),
                    "template_id": item.get("template_id"),
                    "template_name": item.get("template_name"),
                    "database_id": item.get("database_id"),
                    "database_name": item.get("database_name"),
                    "alias": item.get("alias"),
                    "primary_value": item.get("primary_value"),
                    "cleanup_strategy": item.get("cleanup_strategy"),
                    "cleanup_order": item.get("cleanup_order"),
                    "cleanup_status": item.get("cleanup_status"),
                }
                for item in pending_items
            ],
            "risk": "清理会按执行明细记录的数据库、表、主键删除真实测试数据；部分明细可能因策略为不清理而跳过。",
            "force_cleanup": force_cleanup,
        }
        execution_no = detail["execution"].get("execution_no")
        confirm_text = f"CLEANUP_DATA_FACTORY_EXECUTION:{execution_id}:{execution_no}"
        return ok(
            create_dangerous_action_preview("cleanup_data_factory_execution", execution_id, confirm_text, impact),
            "已生成数据工厂清理影响预览",
        )

    @mcp.tool()
    def cleanup_data_factory_execution(
        execution_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
        force_cleanup: bool = False,
    ) -> dict:
        """清理某次数据工厂执行记录创建的数据。必须先调用 preview_cleanup_data_factory_execution_impact。"""
        confirm_error = validate_dangerous_action_confirmation(
            "cleanup_data_factory_execution",
            execution_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        result = DataFactoryCleanup.cleanup_execution(execution_id, force_cleanup=force_cleanup)
        return ok(result, result.get("message") or "数据工厂执行记录清理完成")

    @mcp.tool()
    def get_data_factory_schema() -> dict:
        """返回数据工厂 MCP 常用字段、枚举和变量约定。"""
        return ok(
            {
                "generator_type": {
                    0: "跳过",
                    1: "固定值",
                    2: "随机字符串",
                    3: "随机整数",
                    4: "随机小数",
                    5: "当前时间",
                    6: "相对时间",
                    7: "UUID",
                    9: "枚举值",
                    11: "依赖实体字段",
                    13: "测试数据方法",
                },
                "cleanup_strategy": {1: "执行结束", 2: "手动清理", 3: "不清理"},
                "case_source_type": {1: "API用例", 2: "UI用例", 3: "API接口场景"},
                "execution_source": {1: "模板调试", 2: "手动执行", 3: "系统调用", 4: "API用例", 5: "API接口场景"},
                "cache_variable_pattern": "${{配置名.字段名}}",
                "entity_field_rule_workflow": {
                    "important": "数据工厂实体必须同时有字段规则才能生成完整测试数据。create_data_factory_entity 默认只建实体壳；字段规则需要同步表结构或单独保存。",
                    "recommended_paths": [
                        "批量按表创建：先 list_data_factory_database_tables / get_data_factory_table_schema，再调用 batch_generate_data_factory_entities(sync_fields=True)。",
                        "单表创建并同步字段：调用 create_data_factory_entity(sync_fields=True, test_env=测试环境)。",
                        "手工维护字段：先 create_data_factory_entity，再调用 batch_save_data_factory_fields(entity_id, fields)。",
                    ],
                    "verification": "创建后调用 get_data_factory_entity_detail 或 list_data_factory_fields，确认 fields 不为空并且 generator_type/generator_config 符合业务字段含义。",
                    "template_overrides_scope": "DataFactoryTemplate.field_overrides 和 case 绑定里的 field_overrides 只是在执行模板时覆盖实体字段规则，不能替代实体字段规则本身。",
                    "tools": {
                        "discover_tables": "list_data_factory_database_tables",
                        "discover_schema": "get_data_factory_table_schema",
                        "create_entity_with_schema_fields": "create_data_factory_entity(sync_fields=True, test_env=...)",
                        "batch_create_entities_with_schema_fields": "batch_generate_data_factory_entities(sync_fields=True)",
                        "save_fields": "batch_save_data_factory_fields",
                        "preview_fields": "preview_data_factory_field_values",
                    },
                },
                "template_preview_execute_cleanup_workflow": {
                    "preview_data": "调用 preview_data_factory_template(template_id, overrides, context, test_env) 只预览生成数据，不落库。",
                    "safe_execute": [
                        "调用 preview_run_data_factory_template_impact(template_id, overrides, context, test_env) 获取即将落库的 payload/output/dependencies 和二次确认 token。",
                        "用户确认预览数据无误后，调用 execute_data_factory_template，并原样传回 preview_token 和 confirm_text。",
                        "execute_data_factory_template 会真实落库并返回 execution_id、execution_no、data、output、cache_keys。",
                    ],
                    "cleanup": [
                        "执行后如需清理，先调用 preview_cleanup_data_factory_execution_impact(execution_id) 查看会删除哪些执行明细。",
                        "用户确认后调用 cleanup_data_factory_execution，并原样传回 preview_token 和 confirm_text。",
                    ],
                    "delete_template": [
                        "删除状态模板前必须调用 preview_delete_data_factory_template_impact(template_id)，查看绑定用例配置和历史执行影响。",
                        "用户确认后调用 delete_data_factory_template，并原样传回 preview_token 和 confirm_text。",
                        "如果模板已被用例或场景绑定，删除会被阻止；推荐先停用 set_data_factory_template_status(status=0)。",
                    ],
                    "safety_rule": "真实执行和清理都属于危险操作，不允许跳过预览确认。",
                },
                "field_rule_payload": {
                    "required": ["name"],
                    "common_fields": {
                        "name": "数据库字段名，必填",
                        "label": "字段展示名/注释，不传时通常使用 name",
                        "db_type": "数据库原始类型，例如 BIGINT、VARCHAR(64)",
                        "platform_type": "平台类型：string/integer/decimal/datetime/date/boolean/json/enum",
                        "nullable": "是否允许为空",
                        "primary_key": "是否主键",
                        "autoincrement": "是否自增",
                        "max_length": "最大长度",
                        "enum_values": "枚举值数组",
                        "generator_type": "生成器类型，见 generator_type",
                        "generator_config": "生成器配置，见 generator_config_rule.common_generator_config",
                        "sort": "字段排序",
                    },
                    "examples": {
                        "tenant_id": {
                            "name": "tenant_id",
                            "label": "租户ID",
                            "db_type": "BIGINT",
                            "platform_type": "integer",
                            "nullable": False,
                            "generator_type": 13,
                            "generator_config": {"value": "${{tenant_id}}"},
                            "sort": 1,
                        },
                        "business_name": {
                            "name": "name",
                            "label": "名称",
                            "db_type": "VARCHAR(128)",
                            "platform_type": "string",
                            "nullable": False,
                            "generator_type": 13,
                            "generator_config": {"value": "AUTO${{str_lowercase(10)}}"},
                            "sort": 2,
                        },
                        "dependency_id": {
                            "name": "category_id",
                            "label": "分类ID",
                            "db_type": "BIGINT",
                            "platform_type": "integer",
                            "nullable": False,
                            "generator_type": 11,
                            "generator_config": {"dependency_entity_id": 12, "field": "id"},
                            "sort": 3,
                        },
                    },
                },
                "generator_config_rule": {
                    "how_to_choose": [
                        "主键自增字段通常使用 generator_type=0 跳过，让数据库生成。",
                        "tenant_id、valid、固定业务状态等确定值使用 generator_type=1 固定值，或 generator_type=13 写 ${{tenant_id}} 这类测试数据表达式。",
                        "名称、编号、手机号、邮箱、地址等业务字符串优先使用 generator_type=13 测试数据方法。",
                        "普通随机字符串可用 generator_type=2；普通数值范围可用 3/4；时间字段可用 5/6。",
                        "枚举字段使用 generator_type=9；外键或前置数据依赖使用 generator_type=11。",
                    ],
                    "generator_type_usage": {
                        0: {
                            "name": "跳过",
                            "use_for": "数据库自增主键、数据库默认值、创建时不需要写入的字段。",
                            "generator_config": {"reason": "可选，说明为什么跳过"},
                            "example": {"generator_type": 0, "generator_config": {"reason": "数据库自增主键"}},
                            "result": "该字段不会进入插入 payload。",
                        },
                        1: {
                            "name": "固定值",
                            "use_for": "固定状态、固定租户、固定开关值，或需要明确写死的字段。",
                            "generator_config": {"value": "任意 JSON 值，可为字符串/数字/布尔/null/对象/数组"},
                            "example": {"generator_type": 1, "generator_config": {"value": 1}},
                            "result": "直接返回 value，并按字段 platform_type 做类型转换。",
                        },
                        2: {
                            "name": "随机字符串",
                            "use_for": "不强调语义的随机编码。",
                            "generator_config": {"prefix": "可选前缀，默认空字符串", "length": "随机部分长度，默认 8，必须大于 0"},
                            "example": {"generator_type": 2, "generator_config": {"prefix": "AUTO_", "length": 10}},
                            "result": "prefix + uuid hex 前 length 位。",
                        },
                        3: {
                            "name": "随机整数",
                            "use_for": "数量、排序、范围内整数。",
                            "generator_config": {"min": "最小值，默认 1", "max": "最大值，默认 100，min 不能大于 max"},
                            "example": {"generator_type": 3, "generator_config": {"min": 1, "max": 999}},
                            "result": "闭区间随机整数。",
                        },
                        4: {
                            "name": "随机小数",
                            "use_for": "金额、比例、带小数的数值。",
                            "generator_config": {"min": "最小值，默认 1", "max": "最大值，默认 100", "precision": "小数位，默认 2，不能小于 0"},
                            "example": {"generator_type": 4, "generator_config": {"min": 10, "max": 99, "precision": 2}},
                            "result": "范围内随机 Decimal，并按 precision 保留小数。",
                        },
                        5: {
                            "name": "当前时间",
                            "use_for": "create_time、update_time、生效时间等当前时间字段。",
                            "generator_config": {},
                            "example": {"generator_type": 5, "generator_config": {}},
                            "result": "datetime.now()，再按字段 platform_type 转换。",
                        },
                        6: {
                            "name": "相对时间",
                            "use_for": "过期时间、未来/过去时间。",
                            "generator_config": {"days": "相对天数，默认 0", "hours": "相对小时，默认 0", "minutes": "相对分钟，默认 0"},
                            "example": {"generator_type": 6, "generator_config": {"days": 7, "hours": 0, "minutes": 0}},
                            "result": "datetime.now() + timedelta(days/hours/minutes)。",
                        },
                        7: {
                            "name": "UUID",
                            "use_for": "唯一追踪号、外部唯一编码。",
                            "generator_config": {"dash": "是否保留 UUID 横线，默认 false"},
                            "example": {"generator_type": 7, "generator_config": {"dash": False}},
                            "result": "dash=false 返回 32 位 hex；dash=true 返回标准 UUID。",
                        },
                        9: {
                            "name": "枚举值",
                            "use_for": "状态、类型、开关等有限选项字段。",
                            "generator_config": {
                                "values": "枚举值数组；也可使用字段 enum_values",
                                "options": "可选展示项数组，格式 [{label,value}]",
                                "mode": "fixed 或 random，默认 fixed",
                                "value": "mode=fixed 时的固定值；不传则取第一个 values",
                            },
                            "example": {"generator_type": 9, "generator_config": {"values": [0, 1], "mode": "fixed", "value": 1}},
                            "result": "random 随机取 values；fixed 返回 value 或第一个 values。",
                        },
                        11: {
                            "name": "依赖实体字段",
                            "use_for": "外键字段、需要先创建前置数据再引用其 id/code/name 的字段。",
                            "entity_field_generator_config": {
                                "dependency_entity_id": "依赖的数据工厂实体 ID，必填",
                                "field": "读取依赖实体输出字段，默认 id",
                            },
                            "template_or_case_override_generator_config": {
                                "dependency_entity_id": "依赖的数据工厂实体 ID，必填",
                                "field": "读取依赖实体输出字段，默认 id",
                                "template_id": "可选，指定依赖实体使用哪个状态模板；不传则使用依赖实体默认启用模板",
                                "strategy": "reuse_or_create / must_exist / create_always，默认 reuse_or_create",
                            },
                            "example": {"generator_type": 11, "generator_config": {"dependency_entity_id": 12, "field": "id"}},
                            "result": "执行时先准备依赖实体数据，再把依赖数据中的 field 值写入当前字段。",
                        },
                        13: {
                            "name": "测试数据方法",
                            "use_for": "手机号、邮箱、姓名、地址、身份证、业务编号、缓存变量、编码处理等表达式生成值。MCP 只推荐使用测试数据分类的方法。",
                            "generator_config": {"value": "测试数据表达式字符串，例如 ${{character_email()}} 或 AUTO${{str_lowercase(10)}}"},
                            "example": {"generator_type": 13, "generator_config": {"value": "AUTO${{str_lowercase(10)}}"}},
                            "result": "先返回 value 字符串，再通过测试数据引擎替换 ${{...}} 表达式，最后按 platform_type 转换。",
                        },
                    },
                    "priority": [
                        "字符串/文本/名称/编号/邮箱/手机号/地址等字符串类字段，优先使用 generator_type=13 测试数据方法。",
                        "测试数据方法不合适时，再使用 generator_type=2 随机字符串或 generator_type=1 固定值。",
                        "数值、时间、枚举、依赖字段按字段语义分别使用整数/小数/时间/枚举/依赖实体字段。",
                    ],
                    "string_field_recommendation": {
                        "generator_type": 13,
                        "generator_config": {"value": "${{测试数据方法(...)}}"},
                        "how_to_discover_methods": "调用 MCP 工具 list_test_data_methods(keyword=None, include_hidden=False) 获取测试数据方法类型、分组、参数、expression_template 和 example。",
                        "how_to_preview_expression": "调用 MCP 工具 evaluate_test_data_expression(expression='${{方法名(...)}}') 试算表达式。",
                        "method_result_cast": "生成值会按字段 platform_type 转换后保存；字符串字段通常直接保存表达式计算结果。",
                        "usage_steps": [
                            "调用 list_test_data_methods(keyword='name/phone/email/id 等') 查询可用测试数据方法。",
                            "从返回的 method.expression_template 或 method.example 拿到表达式。",
                            "把表达式写入字段规则 generator_config.value。",
                            "调用 preview_data_factory_field_values(fields=[...]) 或 preview_data_factory_template(template_id=...) 预览生成结果。",
                        ],
                        "expression_examples": [
                            "${{character_email()}}",
                            "${{character_phone()}}",
                            "${{character_male_name()}}",
                            "AUTO${{str_lowercase(10)}}",
                            "${{tenant_id}}",
                        ],
                    },
                    "test_data_method_tool": {
                        "tool": "list_test_data_methods",
                        "purpose": "查询随机测试数据/平台变量方法。只返回测试数据分类下的方法。",
                        "arguments": {
                            "keyword": "可选，用字段含义筛选，例如 email、phone、name、address、id",
                            "include_hidden": "默认 false，不返回内部隐藏方法",
                        },
                        "returns": {
                            "items": "按 type_group -> class_group -> method 分组",
                            "method.expression_template": "参数名模板，例如 ${{character_email()}}",
                            "method.example": "带示例参数的可直接试算表达式",
                            "method.parameter": "方法参数定义",
                        },
                    },
                    "common_generator_config": {
                        0: "跳过，无 generator_config 要求",
                        1: {"value": "固定值"},
                        2: {"prefix": "可选前缀", "length": "随机字符串长度，默认 8"},
                        3: {"min": "最小整数，默认 1", "max": "最大整数，默认 100"},
                        4: {"min": "最小小数，默认 1", "max": "最大小数，默认 100", "precision": "小数位，默认 2"},
                        5: "当前时间，无 generator_config 要求",
                        6: {"days": "相对天数", "hours": "相对小时", "minutes": "相对分钟"},
                        7: {"dash": "是否保留 UUID 横线，默认 false"},
                        9: {"values": "枚举数组", "mode": "random 时随机，否则取 value 或第一个枚举", "value": "可选指定枚举值"},
                        11: {"dependency_entity_id": "依赖实体ID", "field": "取值字段，通常为 id"},
                        13: {"value": "测试数据方法表达式，例如 ${{character_email()}}"},
                    },
                    "string_examples": {
                        "email": {"generator_type": 13, "generator_config": {"value": "${{character_email()}}"}},
                        "phone": {"generator_type": 13, "generator_config": {"value": "${{character_phone()}}"}},
                        "name": {"generator_type": 13, "generator_config": {"value": "${{character_male_name()}}"}},
                        "address": {"generator_type": 13, "generator_config": {"value": "${{character_address()}}"}},
                        "fallback_random_code": {"generator_type": 13, "generator_config": {"value": "AUTO${{str_lowercase(10)}}"}},
                    },
                },
                "dependency_field_rule": {
                    "entity_field_config": {
                        "generator_type": 11,
                        "generator_config": {
                            "dependency_entity_id": "依赖实体ID",
                            "field": "取值字段，通常为 id",
                        },
                    },
                    "template_or_case_override": {
                        "generator_type": 11,
                        "generator_config": {
                            "dependency_entity_id": "继承工厂实体字段规则中的依赖实体ID",
                            "field": "继承工厂实体字段规则中的取值字段",
                            "template_id": "可选；指定依赖实体下的状态模板。不传时使用依赖实体的默认启用模板。",
                            "strategy": "reuse_or_create",
                        },
                    },
                    "default_template": "状态模板 is_default=True 时为该实体默认模板；同一实体只保留一个默认模板。",
                },
                "template_usage_scope": {
                    1: {
                        "name": "用例可直接选择",
                        "meaning": "完整业务对象入口模板，会出现在 API/UI case 的数据工厂选择列表中，可直接绑定到用例执行。",
                        "recommended_for": "普通测试用户会直接消费的场景，例如完整合同流程、完整订单、有效用户。",
                    },
                    2: {
                        "name": "仅场景内部引用",
                        "meaning": "内部编排模板，不出现在 API/UI case 选择列表，只能被其他场景模板作为关联模板引用。",
                        "recommended_for": "子表、中间表、绑定关系、节点配置、字段权限等底层模板。",
                    },
                    "important": [
                        "usage_scope 不等于 is_default。",
                        "is_default 只用于依赖实体字段未指定 template_id 时选择该实体的默认启用模板。",
                        "usage_scope 只控制模板是否出现在 case 选择列表以及模板用途语义。",
                    ],
                },
                "examples": {
                    "field_overrides": {
                        "category_name": {
                            "generator_type": 13,
                            "generator_config": {"value": "AUTO${{str_lowercase(10)}}"},
                        },
                        "category_id": {
                            "generator_type": 11,
                            "generator_config": {
                                "dependency_entity_id": 12,
                                "field": "id",
                            },
                        }
                    },
                    "case_body": {
                        "categoryId": "${{创建一级合同.id}}",
                        "categoryName": "${{创建一级合同.category_name}}",
                    },
                },
            }
        )
