from __future__ import annotations

from typing import Any, Literal

from django.db import transaction
from django.forms import model_to_dict

from src.auto_test.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.auto_test.auto_data_factory.models import (
    DataFactoryCaseConfig,
    DataFactoryDatasourceAlias,
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryField,
    DataFactoryTemplate,
)
from src.auto_test.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.auto_test.auto_data_factory.service.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver, is_missing_value
from src.auto_test.auto_data_factory.service.discover import DataFactoryDiscover
from src.auto_test.auto_data_factory.service.runner import DataFactoryRunner
from src.auto_test.auto_data_factory.views.datasource_alias import DataFactoryDatasourceAliasCRUD
from src.auto_test.auto_data_factory.views.datasource_binding import DataFactoryDatasourceBindingCRUD
from src.auto_test.auto_data_factory.views.entity import DataFactoryEntityCRUD, DataFactoryEntityViews
from src.auto_test.auto_data_factory.views.field import DataFactoryFieldCRUD, DataFactoryFieldViews
from src.auto_test.auto_data_factory.views.template import DataFactoryTemplateCRUD
from src.auto_test.auto_system.models import Database, ProductModule
from src.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionSourceEnum,
)
from src.enums.tools_enum import StatusEnum
from src.mcp_server.common import current_user, fail, ok


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
    return keys


def _data_factory_result_with_cache_keys(result: dict, template: DataFactoryTemplate, name: str | None = None) -> dict:
    data = dict(result or {})
    data["cache_prefix"] = _template_cache_prefix(template, name)
    data["cache_keys"] = _cache_keys_for_template(template, name)
    return data


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
        "status": item.status,
        "cache_prefix": _template_cache_prefix(item, name),
        "cache_keys": _cache_keys_for_template(item, name),
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
        "test_object_id": item.test_object_id,
        "stage": item.stage,
        "status": item.status,
        "cleanup_status": item.cleanup_status,
        "error_message": item.error_message,
        "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
        "cleanup_time": item.cleanup_time.strftime("%Y-%m-%d %H:%M:%S") if item.cleanup_time else None,
    }


def _execution_detail(execution_id: int) -> dict:
    execution = DataFactoryExecution.objects.select_related("template", "project_product", "module", "test_object").get(id=execution_id)
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
        project_product_id: int | None = None,
        module_id: int | None = None,
        datasource_alias_id: int | None = None,
        keyword: str | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询数据工厂实体。"""
        queryset = DataFactoryEntity.objects.select_related("project_product", "module", "datasource_alias").all()
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
        create_type: int = 2,
        delete_type: int = 2,
        cleanup_order: int = 100,
        description: str | None = None,
        status: int = StatusEnum.SUCCESS.value,
    ) -> dict:
        """创建数据工厂实体。"""
        if not ProductModule.objects.filter(id=module_id, project_product_id=project_product_id).exists():
            return fail("模块不属于当前项目/产品", "DATA_FACTORY_MODULE_MISMATCH")
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
                "create_type": create_type,
                "delete_type": delete_type,
                "cleanup_order": cleanup_order,
                "status": status,
            }
        )
        return ok({"entity_id": data["id"], **data}, "数据工厂实体创建成功")

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
        """批量保存数据工厂字段规则。"""
        entity = DataFactoryEntity.objects.get(id=entity_id)
        with transaction.atomic():
            saved = DataFactoryFieldViews.save_schema_fields(entity, fields, replace)
        return ok({"items": saved, "count": len(saved)}, "字段规则保存成功")

    @mcp.tool()
    def preview_data_factory_field_values(fields: list[dict], context: dict | None = None) -> dict:
        """预览字段规则生成值，不落库。"""
        class _Request:
            data = {"fields": fields, "context": context or {}}

        response = DataFactoryFieldViews().preview_values(_Request())  # type: ignore[arg-type]
        return ok(response.data.get("data"), "字段规则预览完成")

    @mcp.tool()
    def list_data_factory_templates(
        project_product_id: int | None = None,
        module_id: int | None = None,
        entity_id: int | None = None,
        keyword: str | None = None,
        enabled_only: bool = True,
    ) -> dict:
        """查询数据工厂状态模板。"""
        queryset = DataFactoryTemplate.objects.select_related("entity", "module", "project_product").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if entity_id is not None:
            queryset = queryset.filter(entity_id=entity_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        return ok({"items": [_template_summary(item) for item in queryset.order_by("-id")]})

    @mcp.tool()
    def get_data_factory_template_detail(template_id: int, name: str | None = None) -> dict:
        """查询数据工厂状态模板详情、实体、字段和可用缓存变量。"""
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
        cleanup_strategy: int = DataFactoryCleanupStrategyEnum.MANUAL.value,
        status: int = StatusEnum.SUCCESS.value,
    ) -> dict:
        """创建数据工厂状态模板。"""
        data = DataFactoryTemplateCRUD.inside_post(
            {
                "project_product": project_product_id,
                "module": module_id,
                "entity": entity_id,
                "name": name,
                "description": description,
                "field_overrides": field_overrides or {},
                "output_config": output_config or [],
                "cleanup_strategy": cleanup_strategy,
                "status": status,
            }
        )
        template = DataFactoryTemplate.objects.get(id=data["id"])
        return ok({"template_id": data["id"], **data, "cache_keys": _cache_keys_for_template(template)}, "状态模板创建成功")

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
        cleanup_strategy: int | None = None,
        status: int | None = None,
    ) -> dict:
        """更新数据工厂状态模板。"""
        payload: dict[str, Any] = {"id": template_id}
        for key, value in {
            "project_product": project_product_id,
            "module": module_id,
            "entity": entity_id,
            "name": name,
            "description": description,
            "field_overrides": field_overrides,
            "output_config": output_config,
            "cleanup_strategy": cleanup_strategy,
            "status": status,
        }.items():
            if value is not None:
                payload[key] = value
        data = DataFactoryTemplateCRUD.inside_put(template_id, payload)
        template = DataFactoryTemplate.objects.get(id=template_id)
        return ok({"template_id": template_id, **data, "cache_keys": _cache_keys_for_template(template)}, "状态模板更新成功")

    @mcp.tool()
    def preview_data_factory_template(
        template_id: int,
        overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """预览数据工厂模板生成结果，不落库。"""
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
    def debug_run_data_factory_template(
        template_id: int,
        overrides: dict | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """调试运行数据工厂模板，会真实落库并生成执行记录。"""
        template = DataFactoryTemplate.objects.get(id=template_id)
        env = _selected_test_env(user_id, test_env)
        result = DataFactoryRunner.debug_run_template(
            template_id=template_id,
            overrides=overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
        return ok(_data_factory_result_with_cache_keys(result, template), "模板调试执行完成")

    @mcp.tool()
    def set_data_factory_template_status(template_id: int, status: Literal[0, 1]) -> dict:
        """启用或停用数据工厂状态模板。"""
        template = DataFactoryTemplate.objects.get(id=template_id)
        template.status = status
        template.save(update_fields=["status", "update_time"])
        return ok({"template_id": template.id, "status": template.status}, "状态模板状态更新成功")

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
    def bind_data_factory_to_api_case(
        source_id: int,
        template_id: int,
        source_type: Literal[1, 3] = DataFactoryCaseSourceTypeEnum.API_CASE.value,
        name: str | None = None,
        stage: int = 1,
        sort: int = 0,
        field_overrides: dict | None = None,
        cleanup_strategy: int | None = DataFactoryCleanupStrategyEnum.MANUAL.value,
        status: int = StatusEnum.SUCCESS.value,
        deduplicate: bool = True,
    ) -> dict:
        """兼容旧 API：给 API case 或 API 接口场景绑定数据工厂前置配置。"""
        return bind_data_factory_to_case_source(
            source_type=source_type,
            source_id=source_id,
            template_id=template_id,
            name=name,
            stage=stage,
            sort=sort,
            field_overrides=field_overrides,
            cleanup_strategy=cleanup_strategy,
            status=status,
            deduplicate=deduplicate,
        )

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
        queryset = DataFactoryExecution.objects.select_related("template", "project_product", "module", "test_object").all()
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
    def cleanup_data_factory_execution(execution_id: int, confirm: bool = False) -> dict:
        """清理某次数据工厂执行记录创建的数据。confirm 必须为 true。"""
        if not confirm:
            return fail("清理数据属于高风险操作，请传 confirm=true 后再执行", "DATA_FACTORY_CLEANUP_NOT_CONFIRMED")
        result = DataFactoryCleanup.cleanup_execution(execution_id)
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
                "examples": {
                    "field_overrides": {
                        "category_name": {
                            "generator_type": 13,
                            "generator_config": {"value": "AUTO_${{str_random_string()}}"},
                        }
                    },
                    "case_body": {
                        "categoryId": "${{创建一级合同.id}}",
                        "categoryName": "${{创建一级合同.category_name}}",
                    },
                },
            }
        )
