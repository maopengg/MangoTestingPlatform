# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务

import copy
import uuid

from django.db import transaction
from pydantic import ValidationError

from src.apps.auto_data_factory.models import (
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.common.enums.data_factory_enum import (
    DataFactoryCleanupStatusEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
)
from src.common.exceptions import ToolsError
from src.common.models.data_factory_model import (
    DataFactoryFieldOverrideRule,
    DataFactoryFieldOverrideRules,
    DataFactoryOutputConfig,
    SCENE_ITEM_OVERRIDES_KEY,
    SCENE_MAIN_OVERRIDES_KEY,
)

from .datasource import DataFactoryDatasource, DataFactoryDatasourceResolver, is_missing_value
from .generator import DataFactoryValueGenerator
from .runtime_cache import DataFactoryRuntimeCache
from .type_cast import DataFactoryTypeCast


class DataFactoryRunner:
    @staticmethod
    def get_template(template_id: int | str | None) -> DataFactoryTemplate:
        if not template_id:
            raise ToolsError(300, "状态模板ID不能为空")
        try:
            return DataFactoryTemplate.objects.select_related(
                'entity',
                'entity__datasource_alias',
                'project_product',
            ).get(id=template_id)
        except DataFactoryTemplate.DoesNotExist as error:
            raise ToolsError(300, "状态模板不存在或已被删除，请刷新列表后重试") from error

    @classmethod
    def get_dependency_template(cls, field, config: dict) -> DataFactoryTemplate:
        template_id = config.get("template_id")
        dependency_entity_id = config.get("dependency_entity_id")
        if not dependency_entity_id:
            raise ToolsError(300, f"字段 {field.name} 未配置依赖实体 dependency_entity_id")
        if template_id:
            try:
                dependency_template = DataFactoryTemplate.objects.select_related(
                    'entity',
                    'project_product',
                    'entity__datasource_alias',
                ).get(id=template_id)
            except DataFactoryTemplate.DoesNotExist as error:
                raise ToolsError(300, f"字段 {field.name} 配置的依赖状态模板不存在或已被删除") from error
        else:
            dependency_template = DataFactoryTemplate.objects.select_related(
                'entity',
                'project_product',
                'entity__datasource_alias',
            ).filter(
                entity_id=dependency_entity_id,
                is_default=True,
                status=1,
            ).first()
            if not dependency_template:
                raise ToolsError(300, f"字段 {field.name} 依赖实体未配置默认状态模板")
        if str(dependency_template.entity_id) != str(dependency_entity_id):
            raise ToolsError(300, f"字段 {field.name} 的依赖状态模板不属于已选择的依赖实体")
        return dependency_template

    @classmethod
    def preview_template(
            cls,
            template_id: int,
            overrides: dict | None = None,
            output_config: list | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            test_data=None,
    ) -> dict:
        template = cls.get_template(template_id)
        if not test_object_id and not is_missing_value(test_env):
            test_object_id = DataFactoryDatasourceResolver.resolve_test_object_id(template.project_product_id, test_env)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        runtime_context = context or {}
        main_overrides, item_overrides = cls.split_scene_overrides(overrides or {})
        result = cls.preview_by_template(
            template,
            main_overrides,
            runtime_context,
            test_object_id,
            set(),
            output_config=output_config,
            test_data=test_data,
        )
        return cls.preview_template_items(
            template=template,
            result=result,
            item_overrides=item_overrides,
            context=runtime_context,
            test_object_id=test_object_id,
            test_data=test_data,
        )

    @staticmethod
    def split_scene_overrides(overrides: dict | None) -> tuple[dict, dict]:
        overrides = overrides or {}
        if SCENE_MAIN_OVERRIDES_KEY in overrides or SCENE_ITEM_OVERRIDES_KEY in overrides:
            return overrides.get(SCENE_MAIN_OVERRIDES_KEY) or {}, overrides.get(SCENE_ITEM_OVERRIDES_KEY) or {}
        return overrides, {}

    @staticmethod
    def get_template_items(template: DataFactoryTemplate) -> list[DataFactoryTemplateItem]:
        return list(
            template.items.select_related(
                'child_template',
                'child_template__entity',
                'child_template__entity__datasource_alias',
                'child_template__project_product',
            ).order_by('sort', 'id')
        )

    @staticmethod
    def get_item_override(item: DataFactoryTemplateItem, item_overrides: dict | None) -> dict:
        item_overrides = item_overrides or {}
        keys = [
            str(item.id),
            item.name,
            str(item.child_template_id),
            item.child_template.name if item.child_template_id else "",
        ]
        for key in keys:
            if key and key in item_overrides:
                return item_overrides.get(key) or {}
        return {}

    @classmethod
    def preview_template_items(
            cls,
            template: DataFactoryTemplate,
            result: dict,
            item_overrides: dict,
            context: dict,
            test_object_id: int | None,
            test_data=None,
    ) -> dict:
        items = []
        items_output = {}
        can_debug_run = result.get("can_debug_run", False)
        dependency_tree = result.get("dependency_tree") or {}
        dependency_tree.setdefault("children", [])
        all_missing_fields = list(result.get("all_missing_fields") or [])

        for item in cls.get_template_items(template):
            overrides = {
                **(item.field_overrides or {}),
                **cls.get_item_override(item, item_overrides),
            }
            item_result = cls.preview_by_template(
                item.child_template,
                overrides,
                context,
                test_object_id,
                set(),
                alias_override=item.name or item.child_template.name,
                test_data=test_data,
            )
            item_result["scene_item"] = {
                "id": item.id,
                "name": item.name,
                "sort": item.sort,
                "child_template_id": item.child_template_id,
            }
            item_tree = item_result.get("dependency_tree") or {}
            item_tree["scene_item_id"] = item.id
            item_tree["scene_item_name"] = item.name
            item_tree["action"] = "create"
            item_tree["message"] = item_tree.get("message") or "场景关联模板"
            dependency_tree["children"].append(item_tree)
            can_debug_run = can_debug_run and item_result.get("can_debug_run", False)
            all_missing_fields.extend(item_result.get("all_missing_fields") or [])
            output_key = item.name or item.child_template.name
            items_output[output_key] = item_result.get("output") or item_result.get("payload") or {}
            items.append({
                "id": item.id,
                "name": item.name,
                "template": item_result.get("template"),
                "entity": item_result.get("entity"),
                "payload": item_result.get("payload"),
                "output": item_result.get("output"),
                "fields": item_result.get("fields"),
                "missing_fields": item_result.get("missing_fields"),
                "can_debug_run": item_result.get("can_debug_run"),
            })

        result["items"] = items
        result["items_output"] = items_output
        result["all_missing_fields"] = all_missing_fields
        result["can_debug_run"] = can_debug_run
        result["dependency_tree"] = dependency_tree
        return result

    @classmethod
    def preview_by_template(
            cls,
            template: DataFactoryTemplate,
            overrides: dict,
            context: dict,
            test_object_id: int | None,
            visiting: set[int],
            alias_override: str | None = None,
            output_config: list | None = None,
            test_data=None,
    ) -> dict:
        if template.id in visiting:
            raise ToolsError(300, f"检测到数据工厂循环依赖：{template.name}")
        visiting.add(template.id)

        try:
            return cls._preview_by_template(
                template,
                overrides,
                context,
                test_object_id,
                visiting,
                alias_override,
                output_config,
                test_data,
            )
        finally:
            visiting.remove(template.id)

    @classmethod
    def _preview_by_template(
            cls,
            template: DataFactoryTemplate,
            overrides: dict,
            context: dict,
            test_object_id: int | None,
            visiting: set[int],
            alias_override: str | None,
            output_config: list | None,
            test_data,
    ) -> dict:
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, None)
        entity = template.entity
        if not entity.table_name:
            raise ToolsError(300, f"实体 {entity.name} 未配置表名")
        database = DataFactoryDatasourceResolver.resolve(entity, test_object_id)
        DataFactoryDatasourceResolver.require_permission(test_object_id, write=False)

        fields = list(entity.datafactoryfield_set.all().order_by('sort', 'id'))
        merged_overrides = {**(template.field_overrides or {}), **overrides}
        fields = cls.build_effective_fields(fields, merged_overrides)
        payload = {}
        field_items = []
        missing_fields = []
        dependencies = []
        dependency_nodes = []
        alias = alias_override or template.name
        if entity.create_type != DataFactoryOperationTypeEnum.SQL.value:
            missing_fields.append({
                "field": "__entity_create_type__",
                "message": "调试运行仅支持 SQL 创建方式，请将工厂实体创建方式调整为 SQL",
            })

        for field in fields:
            if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                field_items.append(cls.build_preview_field(field, None, True, "跳过字段"))
                continue

            try:
                value = cls.preview_field_value(
                    field=field,
                    payload=payload,
                    context=context,
                    test_object_id=test_object_id,
                    visiting=visiting,
                    dependencies=dependencies,
                    dependency_nodes=dependency_nodes,
                    test_data=test_data,
                )
                payload[field.name] = DataFactoryTypeCast.to_jsonable(value)
                if value is None and not field.nullable and not field.primary_key:
                    message = "必填字段生成结果为空"
                    missing_fields.append({"field": field.name, "message": message})
                    field_items.append(cls.build_preview_field(field, value, False, message))
                else:
                    field_items.append(cls.build_preview_field(field, payload[field.name], True, ""))
            except Exception as error:
                message = str(error)
                missing_fields.append({"field": field.name, "message": message})
                field_items.append(cls.build_preview_field(field, None, False, message))

        context[alias] = payload
        all_missing_fields = cls.collect_preview_missing_fields(
            template={
                "id": template.id,
                "name": template.name,
                "alias": alias,
            },
            entity={
                "id": entity.id,
                "name": entity.name,
                "table_name": entity.table_name,
            },
            missing_fields=missing_fields,
            dependencies=dependencies,
        )
        dependency_tree = cls.build_dependency_tree(
            template=template,
            entity=entity,
            alias=alias,
            action="root",
            fields=field_items,
            missing_fields=missing_fields,
            children=dependency_nodes,
        )
        output = cls.build_output(output_config if output_config is not None else template.output_config, payload)
        return {
            "template": {
                "id": template.id,
                "name": template.name,
                "alias": alias,
            },
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "table_name": entity.table_name,
                "primary_key": entity.primary_key,
                "unique_key": entity.unique_key,
            },
            "database": {
                "id": database.id,
                "name": database.name,
                "db_type": database.db_type,
                "host": database.host,
                "port": database.port,
            },
            "payload": payload,
            "output": output,
            "fields": field_items,
            "missing_fields": missing_fields,
            "all_missing_fields": all_missing_fields,
            "dependencies": dependencies,
            "dependency_tree": dependency_tree,
            "context": context,
            "can_debug_run": not missing_fields and all(item.get("can_debug_run", False) for item in dependencies),
        }

    @classmethod
    def preview_field_value(
            cls,
            field,
            payload: dict,
            context: dict,
            test_object_id: int | None,
            visiting: set[int],
            dependencies: list,
            dependency_nodes: list,
            test_data=None,
    ):
        if field.generator_type != DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            value = DataFactoryValueGenerator.generate(field, payload, context)
            return DataFactoryValueGenerator.replace_value(value, test_data)

        config = field.generator_config or {}
        target_field = config.get("field", "id")
        alias = config.get("alias")
        strategy = config.get("strategy", "reuse_or_create")
        if alias and alias in context:
            dependency_nodes.append(cls.build_dependency_tree(
                template=None,
                entity=None,
                alias=alias,
                action="reuse",
                field=field.name,
                target_field=target_field,
                strategy=strategy,
                value=context[alias].get(target_field),
                message="复用上下文已有数据",
                fields=[],
                missing_fields=[],
            ))
            return context[alias].get(target_field)

        dependency_template = cls.get_dependency_template(field, config)
        dependency_alias = alias or dependency_template.name
        if strategy != "create_always" and dependency_alias in context:
            dependency_value = context.get(dependency_alias, {}).get(target_field)
            dependencies.append({
                "template": {
                    "id": dependency_template.id,
                    "name": dependency_template.name,
                    "alias": dependency_alias,
                },
                "entity": {
                    "id": dependency_template.entity.id,
                    "name": dependency_template.entity.name,
                    "table_name": dependency_template.entity.table_name,
                },
                "payload": context.get(dependency_alias, {}),
                "fields": [],
                "missing_fields": [],
                "dependencies": [],
                "dependency_tree": cls.build_dependency_tree(
                    template=dependency_template,
                    entity=dependency_template.entity,
                    alias=dependency_alias,
                    action="reuse",
                    field=field.name,
                    target_field=target_field,
                    strategy=strategy,
                    value=dependency_value,
                    message="复用上下文已有数据",
                    fields=[],
                    missing_fields=[],
                ),
                "context": context,
                "can_debug_run": True,
            })
            dependency_nodes.append(dependencies[-1]["dependency_tree"])
            return dependency_value

        dependency_preview = cls.preview_by_template(
            dependency_template,
            config.get("overrides") or {},
            context,
            test_object_id,
            visiting,
            alias_override=dependency_alias,
            test_data=test_data,
        )
        dependency_preview["dependency_tree"]["field"] = field.name
        dependency_preview["dependency_tree"]["target_field"] = target_field
        dependency_preview["dependency_tree"]["strategy"] = strategy
        dependency_preview["dependency_tree"]["action"] = "create"
        dependencies.append(dependency_preview)
        dependency_nodes.append(dependency_preview["dependency_tree"])

        dependency_value = context.get(dependency_alias, {}).get(target_field)
        if dependency_value is None:
            return f"${{{{{dependency_alias}.{target_field}}}}}"
        return dependency_value

    @staticmethod
    def build_preview_field(field, value, valid: bool, message: str) -> dict:
        return {
            "name": field.name,
            "label": field.label,
            "platform_type": field.platform_type,
            "nullable": field.nullable,
            "primary_key": field.primary_key,
            "generator_type": field.generator_type,
            "generator_config": field.generator_config,
            "value": DataFactoryTypeCast.to_jsonable(value),
            "valid": valid,
            "message": message,
        }

    @staticmethod
    def collect_preview_missing_fields(
            template: dict,
            entity: dict,
            missing_fields: list,
            dependencies: list,
            path: str = "",
    ) -> list:
        template_name = template.get("name") or template.get("alias") or ""
        current_path = f"{path} / {template_name}" if path else template_name
        rows = []
        for item in missing_fields or []:
            rows.append({
                "template_id": template.get("id"),
                "template_name": template_name,
                "entity_id": entity.get("id"),
                "entity_name": entity.get("name"),
                "table_name": entity.get("table_name"),
                "alias": template.get("alias"),
                "field": item.get("field"),
                "message": item.get("message", ""),
                "path": current_path,
            })
        for dependency in dependencies or []:
            rows.extend(DataFactoryRunner.collect_preview_missing_fields(
                template=dependency.get("template") or {},
                entity=dependency.get("entity") or {},
                missing_fields=dependency.get("missing_fields") or [],
                dependencies=dependency.get("dependencies") or [],
                path=current_path,
            ))
        return rows

    @classmethod
    def build_effective_fields(cls, fields: list, overrides: dict | None) -> list:
        rules = cls.parse_field_override_rules(overrides)
        if not rules:
            return fields

        effective_fields = []
        for field in fields:
            rule = rules.get(field.name)
            if not rule:
                effective_fields.append(field)
                continue

            effective_field = copy.copy(field)
            effective_field.generator_type = rule.generator_type
            if rule.generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
                effective_field.generator_config = {
                    **(field.generator_config or {}),
                    **(rule.generator_config or {}),
                }
            else:
                effective_field.generator_config = rule.generator_config or {}
            effective_fields.append(effective_field)
        return effective_fields

    @staticmethod
    def parse_field_override_rules(overrides: dict | None) -> dict[str, DataFactoryFieldOverrideRule]:
        if not overrides:
            return {}
        try:
            return DataFactoryFieldOverrideRules.model_validate(overrides).to_dict()
        except ValidationError as error:
            raise ToolsError(300, f"字段覆盖规则格式错误：{error}") from error

    @staticmethod
    def build_output(output_config: list | None, payload: dict) -> dict:
        if not output_config:
            return {}
        try:
            items = DataFactoryOutputConfig.model_validate(output_config).to_list()
        except ValidationError as error:
            raise ToolsError(300, f"输出配置格式错误：{error}") from error

        output = {}
        for item in items:
            output[item.key] = payload.get(item.field)
        return output

    @staticmethod
    def build_dependency_tree(
            template,
            entity,
            alias: str,
            action: str,
            children: list | None = None,
            field: str | None = None,
            target_field: str | None = None,
            strategy: str | None = None,
            value=None,
            message: str = "",
            fields: list | None = None,
            missing_fields: list | None = None,
    ) -> dict:
        fields = fields or []
        missing_fields = missing_fields or []
        missing_count = len(missing_fields)
        status = "warning" if missing_count else "valid"
        if message and action not in ["root", "create", "reuse"]:
            status = "error"
        return {
            "template_id": template.id if template else None,
            "template_name": template.name if template else alias,
            "entity_id": entity.id if entity else None,
            "entity_name": entity.name if entity else None,
            "table_name": entity.table_name if entity else None,
            "alias": alias,
            "field": field,
            "target_field": target_field,
            "strategy": strategy,
            "action": action,
            "reused": action == "reuse",
            "value": DataFactoryTypeCast.to_jsonable(value),
            "message": message,
            "fields": fields,
            "missing_fields": missing_fields,
            "missing_count": missing_count,
            "status": status,
            "children": children or [],
        }

    @classmethod
    @transaction.atomic
    def debug_run_template(
            cls,
            template_id: int,
            overrides: dict | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            test_data=None,
    ) -> dict:
        template = cls.get_template(template_id)
        if not test_object_id and not is_missing_value(test_env):
            test_object_id = DataFactoryDatasourceResolver.resolve_test_object_id(template.project_product_id, test_env)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        main_overrides, item_overrides = cls.split_scene_overrides(overrides or {})
        execution = DataFactoryExecution.objects.create(
            execution_no=cls.build_execution_no(),
            source_type=DataFactoryExecutionSourceEnum.TEMPLATE_DEBUG.value,
            source_id=template.id,
            template=template,
            project_product=template.project_product,
            module=template.module or template.entity.module,
            stage=DataFactoryExecutionStageEnum.DEBUG.value,
            status=DataFactoryExecutionStatusEnum.PROCEED.value,
            context=context or {},
        )

        try:
            runtime_context = context or {}
            data = cls.create_by_template(
                template,
                execution,
                main_overrides,
                runtime_context,
                test_object_id,
                test_data=test_data,
            )
            items = cls.create_template_items(
                template,
                execution,
                item_overrides,
                runtime_context,
                test_object_id,
                test_data,
            )
            output = cls.build_output(template.output_config, data)
            execution.context = runtime_context
            execution.status = DataFactoryExecutionStatusEnum.SUCCESS.value
            execution.save()
            return {
                "execution_id": execution.id,
                "execution_no": execution.execution_no,
                "context": execution.context,
                "data": data,
                "output": output,
                "items": items,
                "items_output": {item["name"]: item.get("output") or item.get("data") for item in items},
            }
        except Exception as error:
            execution.status = DataFactoryExecutionStatusEnum.FAIL.value
            execution.error_message = str(error)
            execution.save()
            raise

    @classmethod
    @transaction.atomic
    def run_template(
            cls,
            template_id: int,
            source_type: int,
            source_id: int | None = None,
            stage: int = DataFactoryExecutionStageEnum.CREATE.value,
            overrides: dict | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            alias_override: str | None = None,
            cleanup_strategy_override: int | None = None,
            test_data=None,
    ) -> dict:
        template = cls.get_template(template_id)
        if not test_object_id and not is_missing_value(test_env):
            test_object_id = DataFactoryDatasourceResolver.resolve_test_object_id(template.project_product_id, test_env)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        main_overrides, item_overrides = cls.split_scene_overrides(overrides or {})
        execution = DataFactoryExecution.objects.create(
            execution_no=cls.build_execution_no(),
            source_type=source_type,
            source_id=source_id,
            template=template,
            project_product=template.project_product,
            module=template.module or template.entity.module,
            stage=stage,
            status=DataFactoryExecutionStatusEnum.PROCEED.value,
            context=context or {},
        )

        try:
            runtime_context = context or {}
            data = cls.create_by_template(
                template,
                execution,
                main_overrides,
                runtime_context,
                test_object_id,
                alias_override=alias_override,
                cleanup_strategy_override=cleanup_strategy_override,
                test_data=test_data,
            )
            items = cls.create_template_items(
                template,
                execution,
                item_overrides,
                runtime_context,
                test_object_id,
                test_data,
            )
            output = cls.build_output(template.output_config, data)
            execution.context = runtime_context
            execution.status = DataFactoryExecutionStatusEnum.SUCCESS.value
            execution.save()
            return {
                "execution_id": execution.id,
                "execution_no": execution.execution_no,
                "context": execution.context,
                "data": data,
                "output": output,
                "items": items,
                "items_output": {item["name"]: item.get("output") or item.get("data") for item in items},
            }
        except Exception as error:
            execution.status = DataFactoryExecutionStatusEnum.FAIL.value
            execution.error_message = str(error)
            execution.save()
            raise

    @classmethod
    def create_template_items(
            cls,
            template: DataFactoryTemplate,
            execution: DataFactoryExecution,
            item_overrides: dict,
            context: dict,
            test_object_id: int | None,
            test_data=None,
    ) -> list[dict]:
        results = []
        for item in cls.get_template_items(template):
            overrides = {
                **(item.field_overrides or {}),
                **cls.get_item_override(item, item_overrides),
            }
            data = cls.create_by_template(
                item.child_template,
                execution,
                overrides,
                context,
                test_object_id,
                alias_override=item.name or item.child_template.name,
                cleanup_strategy_override=template.cleanup_strategy,
                test_data=test_data,
            )
            results.append({
                "id": item.id,
                "name": item.name or item.child_template.name,
                "template_id": item.child_template_id,
                "data": data,
                "output": cls.build_output(item.child_template.output_config, data),
            })
        return results

    @classmethod
    def create_by_template(
            cls,
            template: DataFactoryTemplate,
            execution: DataFactoryExecution,
            overrides: dict,
            context: dict,
            test_object_id: int | None,
            alias_override: str | None = None,
            visiting: set[int] | None = None,
            cleanup_strategy_override: int | None = None,
            test_data=None,
    ) -> dict:
        visiting = visiting or set()
        if template.id in visiting:
            raise ToolsError(300, f"检测到数据工厂循环依赖：{template.name}")
        visiting.add(template.id)

        try:
            return cls._create_by_template(
                template,
                execution,
                overrides,
                context,
                test_object_id,
                alias_override,
                visiting,
                cleanup_strategy_override,
                test_data,
            )
        finally:
            visiting.remove(template.id)

    @classmethod
    def _create_by_template(
            cls,
            template: DataFactoryTemplate,
            execution: DataFactoryExecution,
            overrides: dict,
            context: dict,
            test_object_id: int | None,
            alias_override: str | None,
            visiting: set[int],
            cleanup_strategy_override: int | None,
            test_data,
    ) -> dict:
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, None)
        entity = template.entity
        if entity.create_type != DataFactoryOperationTypeEnum.SQL.value:
            raise ToolsError(300, "当前阶段仅支持 SQL 创建方式")
        if not entity.table_name:
            raise ToolsError(300, f"实体 {entity.name} 未配置表名")
        database = DataFactoryDatasourceResolver.resolve(entity, test_object_id)
        DataFactoryDatasourceResolver.require_permission(test_object_id, write=True)

        fields = list(entity.datafactoryfield_set.all().order_by('sort', 'id'))
        merged_overrides = {**(template.field_overrides or {}), **overrides}
        fields = cls.build_effective_fields(fields, merged_overrides)
        cls.resolve_dependencies(fields, execution, context, test_object_id, visiting, test_data)
        payload = DataFactoryValueGenerator.build_payload(fields, None, context, test_data)
        insert_result = cls.insert(entity, database, payload)
        created = insert_result["created"]
        jsonable_insert_data = DataFactoryTypeCast.to_jsonable(payload)
        jsonable_payload = DataFactoryTypeCast.to_jsonable({**payload, **created})
        alias = alias_override or template.name

        DataFactoryExecutionItem.objects.create(
            execution=execution,
            template=template,
            database=database,
            alias=alias,
            primary_value=str(created.get(entity.primary_key) or ""),
            data=jsonable_payload,
            insert_data=jsonable_insert_data,
            insert_sql=insert_result.get("insert_sql"),
            insert_sql_params=insert_result.get("insert_sql_params") or {},
            cleanup_strategy=cleanup_strategy_override
            if cleanup_strategy_override is not None else template.cleanup_strategy,
            cleanup_order=entity.cleanup_order,
            cleanup_status=DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
        )
        context[alias] = jsonable_payload
        return jsonable_payload

    @classmethod
    def resolve_dependencies(
            cls,
            fields: list,
            execution: DataFactoryExecution,
            context: dict,
            test_object_id: int | None,
            visiting: set[int],
            test_data=None,
    ) -> None:
        for field in fields:
            if field.generator_type != DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
                continue

            config = field.generator_config or {}
            alias = config.get("alias")
            strategy = config.get("strategy", "reuse_or_create")
            if alias and strategy != "create_always" and alias in context:
                continue
            if strategy == "must_exist":
                raise ToolsError(300, f"字段 {field.name} 依赖上下文不存在：{alias}")

            dependency_template = cls.get_dependency_template(field, config)
            dependency_alias = alias or dependency_template.name
            if strategy != "create_always" and dependency_alias in context:
                config["alias"] = dependency_alias
                field.generator_config = config
                continue

            config["alias"] = dependency_alias
            field.generator_config = config
            dependency_overrides = config.get("overrides") or {}
            cls.create_by_template(
                dependency_template,
                execution,
                dependency_overrides,
                context,
                test_object_id,
                alias_override=dependency_alias,
                visiting=visiting,
                test_data=test_data,
            )

    @classmethod
    def insert(cls, entity, database, payload: dict) -> dict:
        try:
            from sqlalchemy import MetaData, Table, insert
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error

        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(database)
        try:
            metadata = MetaData()
            table = Table(entity.table_name, metadata, autoload_with=engine)
            statement = insert(table).values(**payload)
            insert_sql, insert_sql_params = cls.compile_insert_sql(statement, engine.dialect)
            with engine.begin() as connection:
                result = connection.execute(statement)
                created = dict(payload)
                if result.inserted_primary_key and entity.primary_key:
                    created[entity.primary_key] = result.inserted_primary_key[0]
                return {
                    "created": created,
                    "insert_sql": insert_sql,
                    "insert_sql_params": insert_sql_params,
                }
        except Exception as error:
            raise ToolsError(300, f"SQL创建数据失败：{error}") from error
        finally:
            if not managed_by_worker:
                engine.dispose()

    @staticmethod
    def compile_insert_sql(statement, dialect):
        compiled = statement.compile(dialect=dialect)
        return str(compiled), DataFactoryTypeCast.to_jsonable(dict(compiled.params or {}))

    @staticmethod
    def build_execution_no() -> str:
        return f"DF{uuid.uuid4().hex[:24].upper()}"
