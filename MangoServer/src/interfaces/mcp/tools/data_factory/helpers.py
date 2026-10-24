from __future__ import annotations

import hashlib
import json

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryTemplateConfigStatusEnum,
)
from src.apps.data_factory.models import (
    DataFactoryCaseConfig,
    DataFactoryExecution,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.preview import DataFactoryPreviewService
from src.common.exceptions import MangoServerError
from src.common.exceptions.normalization import normalize_expected_exception
from src.interfaces.mcp.common import (
    current_user,
    fail,
    ok,
)


def _selected_test_env(user_id: int | None = None, test_env: int | None = None) -> int | None:
    if test_env is not None:
        return test_env
    try:
        user = current_user(user_id)
    except Exception:
        return None
    from src.apps.user.services.user_cache import UserCacheService

    return UserCacheService.selected_environment(user)


def _template_cache_prefix(template: DataFactoryTemplate, name: str | None = None) -> str:
    return name or template.name


def _cache_keys_for_template(template: DataFactoryTemplate, name: str | None = None) -> list[str]:
    prefix = _template_cache_prefix(template, name)
    keys = [
        f"${{{{{prefix}}}}}",
        f"${{{{{prefix}.__execution_id}}}}",
        f"${{{{{prefix}.__execution_no}}}}",
    ]
    for field_name in DataFactoryQuerySelector.data_factory_field().filter(entity_id=template.entity_id).order_by(
            "sort", "id").values_list("name", flat=True):
        keys.append(f"${{{{{prefix}.{field_name}}}}}")
    for scene_item in template.items.select_related("child_template", "child_template__entity").order_by("sort", "id"):
        item_prefix = f"{prefix}.{scene_item.name or scene_item.child_template.name}"
        keys.append(f"${{{{{item_prefix}}}}}")
        for field_name in DataFactoryQuerySelector.data_factory_field().filter(
                entity_id=scene_item.child_template.entity_id).order_by("sort", "id").values_list("name", flat=True):
            keys.append(f"${{{{{item_prefix}.{field_name}}}}}")
    return keys


def _data_factory_result_with_cache_keys(result: dict, template: DataFactoryTemplate, name: str | None = None) -> dict:
    data = dict(result or {})
    data["cache_prefix"] = _template_cache_prefix(template, name)
    data["cache_keys"] = _cache_keys_for_template(template, name)
    return data


def _preview_data_factory_template_result(
        template_id: int,
        overrides: dict | None = None,
        output_config: list | None = None,
        post_insert_updates: list | None = None,
        context: dict | None = None,
        test_object_id: int | None = None,
        test_env: int | None = None,
        user_id: int | None = None,
) -> dict:
    template = DataFactoryQuerySelector.data_factory_template().get(id=template_id)
    env = _selected_test_env(user_id, test_env)
    try:
        result = DataFactoryPreviewService.preview_template(
            template_id=template_id,
            overrides=overrides or {},
            output_config=output_config,
            post_insert_updates=post_insert_updates,
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
    except MangoServerError as error:
        normalized = normalize_expected_exception(error)
        return fail(normalized.message, normalized.error_code, normalized.details)
    return ok(_data_factory_result_with_cache_keys(result, template), "模板预览完成")


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
        "post_insert_updates": item.post_insert_updates,
        "cleanup_strategy": item.cleanup_strategy,
        "is_default": item.is_default,
        "usage_scope": item.usage_scope,
        "status": item.status,
        "config_status": item.config_status,
        "config_status_name": DataFactoryTemplateConfigStatusEnum.get_value(item.config_status),
        "items": [
            _template_item_summary(scene_item)
            for scene_item in
            item.items.select_related("child_template", "child_template__entity").order_by("sort", "id")
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
        if not ApiQuerySelector.api_case().filter(id=source_id).exists():
            return "API case 不存在"
    elif source_type == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value:
        if not ApiQuerySelector.api_case_detailed_parameter().filter(id=source_id).exists():
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
    from src.apps.data_factory.services.execution_snapshot import get_insert_snapshot

    execution = DataFactoryQuerySelector.data_factory_execution().select_related("template", "project_product",
                                                                                 "module").get(id=execution_id)
    items = []
    sql_records_by_item = {}
    sql_executions = []
    for sql_record in DataFactoryQuerySelector.sql_execution_record().filter(
            source_type='data_factory',
            source_detail__execution_id=execution_id,
    ).order_by('create_time', 'id'):
        item_id = (sql_record.source_detail or {}).get('execution_item_id')
        record_payload = {
            'id': sql_record.id,
            'execution_item_id': item_id,
            'stage': sql_record.source_stage,
            'sql': sql_record.sql_text,
            'parameters': sql_record.sql_parameters,
            'status': sql_record.status,
            'duration_ms': float(sql_record.duration_ms or 0),
            'affected_rows': sql_record.affected_rows,
            'result_preview': sql_record.result_preview,
            'result_truncated': sql_record.result_truncated,
            'error_message': sql_record.error_message,
            'is_slow': sql_record.is_slow,
        }
        sql_executions.append(record_payload)
        if item_id:
            sql_records_by_item.setdefault(int(item_id), []).append(record_payload)
    for item in DataFactoryQuerySelector.data_factory_execution_item().select_related(
            "template",
            "template__entity",
            "database",
    ).filter(execution_id=execution_id).order_by("cleanup_order", "id"):
        snapshot = dict(get_insert_snapshot(item))
        entity = item.template.entity if item.template_id and item.template else None
        snapshot.setdefault("database_id", item.database_id)
        snapshot.setdefault("database_name", get_insert_snapshot(item).get('database_name'))
        snapshot.setdefault("table_name", entity.table_name if entity else None)
        snapshot.setdefault("primary_key", entity.primary_key if entity else None)
        items.append(
            {
                "id": item.id,
                "template_id": item.template_id,
                "template_name": item.template.name if item.template_id else None,
                "database_id": item.database_id,
                "database_name": get_insert_snapshot(item).get('database_name'),
                "alias": item.alias,
                "primary_value": item.primary_value,
                "storage_snapshot": snapshot,
                "data": item.data,
                "cleanup_strategy": item.cleanup_strategy,
                "cleanup_order": item.cleanup_order,
                "cleanup_status": item.cleanup_status,
                "cleanup_error": item.cleanup_error,
                "sql_executions": sql_records_by_item.get(item.id, []),
            }
        )
    cache_keys = []
    if execution.template_id:
        cache_keys = _cache_keys_for_template(execution.template)
    return {
        "execution": _execution_summary(execution),
        "items": items,
        "context": execution.context,
        "cache_keys": cache_keys,
        "sql_executions": sql_executions,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
