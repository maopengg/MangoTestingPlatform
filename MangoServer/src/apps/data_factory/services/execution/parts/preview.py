import copy
from src.apps.data_factory.formatters import preview_cleanup_rules

from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
    DataFactoryTemplateConfigStatusEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_UNAVAILABLE,
    DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_CONFIG_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_TEMPLATE_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_TEMPLATE_RELATION_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_CONFIG_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_DELETE_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_CONFIG_TEMPLATE_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_RELATION_EXECUTION_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_RELATION_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_TYPE_NODE_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_STATUS_CONFIG_TEMPLATE_DELETE_NOT_FOUND,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)
from src.apps.data_factory.schemas.configuration import (
    SCENE_ITEM_OVERRIDES_KEY,
    SCENE_MAIN_OVERRIDES_KEY,
)
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.services.assets.entity import DataFactoryEntityService
from src.apps.data_factory.services.execution.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.execution.runtime_cache import DataFactoryRuntimeCache
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务


class DataFactoryRunnerPreviewMixin:
    @classmethod
    def require_template_entities_available(
            cls,
            template: DataFactoryTemplate,
            test_object_id: int | None = None,
            visiting: set[int] | None = None,
            allow_disabled_template_ids: set[int] | None = None,
    ) -> None:
        visiting = visiting or set()
        allow_disabled_template_ids = allow_disabled_template_ids or set()
        if template.id in visiting:
            return
        visiting.add(template.id)
        if template.id not in allow_disabled_template_ids:
            if getattr(template, "status", StatusEnum.SUCCESS.value) != StatusEnum.SUCCESS.value:
                raise DataFactoryError(DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED,
                                       value=(template.name, "场景模板已停用"))
            if getattr(
                    template,
                    "config_status",
                    DataFactoryTemplateConfigStatusEnum.READY.value,
            ) != DataFactoryTemplateConfigStatusEnum.READY.value:
                raise DataFactoryError(DATA_FACTORY_SCENARIO_TEMPLATE_NOT_ALLOWED,
                                       value=(template.name, "配置未通过完整性校验"))
        if template.entity.status != StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_FACTORY_ENTITY_UNAVAILABLE,
                                   value=DataFactoryEntityService.unavailable_error_values(template.entity),
                                   )
        for item in cls.get_template_items(template):
            cls.require_template_entities_available(
                item.child_template,
                test_object_id,
                visiting,
                allow_disabled_template_ids,
            )

    @staticmethod
    def get_template(template_id: int | str | None) -> DataFactoryTemplate:
        if not template_id:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_REQUIRED)
        try:
            return DataFactoryTemplate.objects.select_related(
                'entity',
                'entity__datasource_alias',
                'project_product',
            ).get(id=template_id)
        except DataFactoryTemplate.DoesNotExist as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_STATUS_TEMPLATE_DELETE_NOT_FOUND) from error

    @classmethod
    def get_dependency_template(cls, field, config: dict) -> DataFactoryTemplate:
        template_id = config.get("template_id")
        dependency_entity_id = config.get("dependency_entity_id")
        if not dependency_entity_id:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_CONFIG_REQUIRED, value=(field.name,))
        if template_id:
            try:
                dependency_template = DataFactoryTemplate.objects.select_related(
                    'entity',
                    'project_product',
                    'entity__datasource_alias',
                ).get(id=template_id)
            except DataFactoryTemplate.DoesNotExist as error:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_STATUS_CONFIG_TEMPLATE_DELETE_NOT_FOUND,
                                       value=(field.name,)) from error
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
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_CONFIG_TEMPLATE_REQUIRED,
                                       value=(field.name,))
        if str(dependency_template.entity_id) != str(dependency_entity_id):
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_FIELD_STATUS_TEMPLATE_INVALID,
                                   value=(field.name,))
        return dependency_template

    @classmethod
    def preview_template(
            cls,
            template_id: int,
            overrides: dict | None = None,
            output_config: list | None = None,
            post_insert_updates: list | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            test_data=None,
            activation_validation: bool = False,
    ) -> dict:
        template = cls.get_template(template_id)
        if not test_object_id and not is_missing_value(test_env):
            test_object_id = DataFactoryDatasourceResolver.resolve_test_object_id(template.project_product_id, test_env)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        with DataFactoryRuntimeCache.bind_context(test_data, context):
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
                activation_validation=activation_validation,
            )
            result = cls.preview_template_items(
                template=template,
                result=result,
                item_overrides=item_overrides,
                context=runtime_context,
                test_object_id=test_object_id,
                test_data=test_data,
                activation_validation=activation_validation,
            )
            update_preview = cls.preview_post_insert_updates(
                template,
                post_insert_updates if post_insert_updates is not None else template.post_insert_updates,
                main_overrides,
                item_overrides,
            )
            result["post_insert_updates"] = update_preview
            result["can_debug_run"] = result.get("can_debug_run", False) and all(
                item.get("valid", False) for item in update_preview
            )
            result["configuration_valid"] = result.get("configuration_valid", False) and all(
                item.get("valid", False) for item in update_preview
            )
            return result

    @staticmethod
    def split_scene_overrides(overrides: dict | None) -> tuple[dict, dict]:
        overrides = overrides or {}
        if SCENE_MAIN_OVERRIDES_KEY in overrides or SCENE_ITEM_OVERRIDES_KEY in overrides:
            return overrides.get(SCENE_MAIN_OVERRIDES_KEY) or {}, overrides.get(SCENE_ITEM_OVERRIDES_KEY) or {}
        return overrides, {}

    @staticmethod
    def get_template_items(template: DataFactoryTemplate) -> list[DataFactoryTemplateItem]:
        return DataFactoryExecutionMetadata.scene_value(template.id, 'items', lambda: list(
            template.items.select_related(
                'child_template',
                'child_template__entity',
                'child_template__entity__datasource_alias',
                'child_template__project_product',
            ).order_by('sort', 'id')
        ))

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
    def prepare_scene_item_overrides(
            cls,
            template: DataFactoryTemplate,
            item: DataFactoryTemplateItem,
            overrides: dict | None,
            root_alias: str | None = None,
    ) -> dict:
        """将场景节点引用转换为运行器可复用的上下文 alias。"""
        prepared = copy.deepcopy(overrides or {})
        node_rules = [
            (field_name, rule)
            for field_name, rule in prepared.items()
            if isinstance(rule, dict)
               and rule.get("generator_type") == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value
               and isinstance(rule.get("generator_config"), dict)
               and rule["generator_config"].get("source_node")
        ]
        if not node_rules:
            return prepared

        item_positions, nodes = DataFactoryExecutionMetadata.scene_value(template.id, 'reference_plan', lambda: (
            {scene_item.id: index for index, scene_item in enumerate(cls.get_template_items(template))},
            cls.build_scene_node_registry(template),
        ))
        current_position = item_positions.get(item.id)
        if current_position is None:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_TEMPLATE_RELATION_INVALID,
                                   value=(item.id, template.name))

        if root_alias:
            nodes = [{**nodes[0], 'alias': root_alias}, *nodes[1:]]
        target_fields = {
            field.name: field
            for field in DataFactoryExecutionMetadata.fields(item.child_template.entity)
        }
        for field_name, rule in node_rules:
            config = rule["generator_config"]
            source = cls.resolve_scene_node(nodes, config["source_node"])
            source_item = source.get("item")
            if source_item and item_positions.get(source_item.id, current_position) >= current_position:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_RELATION_EXECUTION_INVALID,
                                       value=(item.name or item.id, field_name))
            source_field_name = config.get("source_field") or "id"
            source_field = DataFactoryExecutionMetadata.field(source['entity'], source_field_name)
            if not source_field:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_NODE_NOT_FOUND,
                                       value=(config['source_node'], source_field_name))
            target_field = target_fields.get(field_name)
            if not target_field:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_RELATION_NOT_FOUND,
                                       value=(item.name or item.id, field_name))
            if target_field.platform_type != source_field.platform_type:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_FIELD_TYPE_NODE_INVALID,
                                       value=(config['source_node'], source_field_name, source_field.platform_type,
                                              field_name, target_field.platform_type))
            config["alias"] = source["alias"]
            config["field"] = source_field_name
            config["strategy"] = "must_exist"
        return prepared

    @classmethod
    def preview_template_items(
            cls,
            template: DataFactoryTemplate,
            result: dict,
            item_overrides: dict,
            context: dict,
            test_object_id: int | None,
            test_data=None,
            activation_validation: bool = False,
    ) -> dict:
        items = []
        items_output = {}
        can_debug_run = result.get("can_debug_run", False)
        configuration_valid = result.get("configuration_valid", can_debug_run)
        runtime_context_required = result.get("runtime_context_required", False)
        dependency_tree = result.get("dependency_tree") or {}
        dependency_tree.setdefault("children", [])
        all_missing_fields = list(result.get("all_missing_fields") or [])

        for item in cls.get_template_items(template):
            overrides = {
                **(item.field_overrides or {}),
                **cls.get_item_override(item, item_overrides),
            }
            overrides = cls.prepare_scene_item_overrides(template, item, overrides)
            item_result = cls.preview_by_template(
                item.child_template,
                overrides,
                context,
                test_object_id,
                set(),
                alias_override=item.name or item.child_template.name,
                test_data=test_data,
                activation_validation=activation_validation,
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
            configuration_valid = configuration_valid and item_result.get("configuration_valid", False)
            runtime_context_required = runtime_context_required or item_result.get("runtime_context_required", False)
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
        result["configuration_valid"] = configuration_valid
        result["runtime_context_required"] = runtime_context_required
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
            activation_validation: bool = False,
    ) -> dict:
        if template.id in visiting:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_INVALID, value=(template.name,))
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
                activation_validation,
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
            activation_validation: bool = False,
    ) -> dict:
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, None)
        entity = template.entity
        if not entity.table_name:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_ENTITY_CONFIG_REQUIRED, value=(entity.name,))
        binding = DataFactoryDatasourceResolver.resolve_entity_binding(entity, test_object_id)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        database = DatasourceTargetService.resolve(binding, schema_name=entity.schema_name)

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
                "message": "调试运行仅支持 SQL 创建方式，请将数据实体创建方式调整为 SQL",
            })

        for field in fields:
            if field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                field_items.append(cls.build_preview_field(field, None, True, "跳过字段"))
                continue

            try:
                if activation_validation and cls.activation_field_requires_context(template, field):
                    # 保留待执行字段的身份，供后续节点复用；不能把未执行误判为缺值。
                    payload[field.name] = f"${{{{{alias}.{field.name}}}}}"
                    item = cls.build_preview_field(field, None, True, "需在用例运行上下文中校验")
                    item["deferred"] = True
                    field_items.append(item)
                    continue
                value = cls.preview_field_value(
                    field=field,
                    payload=payload,
                    context=context,
                    test_object_id=test_object_id,
                    visiting=visiting,
                    dependencies=dependencies,
                    dependency_nodes=dependency_nodes,
                    test_data=test_data,
                    activation_validation=activation_validation,
                )
                payload[field.name] = DataFactoryTypeCast.to_jsonable(value)
                if value is None and not field.nullable and not field.primary_key:
                    message = "必填字段生成结果为空"
                    missing_fields.append({"field": field.name, "message": message})
                    field_items.append(cls.build_preview_field(field, value, False, message))
                else:
                    item = cls.build_preview_field(field, payload[field.name], True, "")
                    if activation_validation and isinstance(value, str) and "${{" in value and "}}" in value:
                        item["deferred"] = True
                        item["message"] = "需在用例运行上下文中校验"
                    field_items.append(item)
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
        configuration_valid = not missing_fields and all(
            item.get("configuration_valid", item.get("can_debug_run", False)) for item in dependencies
        )
        runtime_context_required = any(item.get("deferred", False) for item in field_items) or any(
            item.get("runtime_context_required", False) for item in dependencies
        )
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
                "name": database.database_name,
                "db_type": database.db_type,
                "host": database.host,
                "port": database.port,
            },
            "resource_cleanup_preview": preview_cleanup_rules(
                getattr(template, 'cleanup_resources', []) or [], entity.primary_key, payload),
            "payload": payload,
            "output": output,
            "fields": field_items,
            "missing_fields": missing_fields,
            "all_missing_fields": all_missing_fields,
            "dependencies": dependencies,
            "dependency_tree": dependency_tree,
            "context": context,
            "configuration_valid": configuration_valid,
            "runtime_context_required": runtime_context_required,
            "can_debug_run": configuration_valid and not runtime_context_required,
        }

    @staticmethod
    def activation_field_requires_context(template, field) -> bool:
        config = field.generator_config or {}
        if field.generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            # 内部叶子可先启用；根场景编排仍会验证来源字段、类型和执行顺序。
            return bool(
                config.get("source_node")) and template.usage_scope == DataFactoryTemplateUsageScopeEnum.INTERNAL.value
        if field.generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
            value = DataFactoryValueGenerator.generate(field, {}, {})
        elif field.generator_type == DataFactoryGeneratorTypeEnum.FIXED.value:
            value = DataFactoryValueGenerator.generate(field, {}, {})
        else:
            return False
        return isinstance(value, str) and "${{" in value and "}}" in value

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
            activation_validation: bool = False,
    ):
        if field.generator_type != DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
            value = DataFactoryValueGenerator.generate(field, payload, context)
            return DataFactoryValueGenerator.replace_value(value, test_data)

        config = field.generator_config or {}
        target_field = config.get("field", "id")
        alias = config.get("alias")
        strategy = config.get("strategy", "reuse_or_create")
        if config.get("source_node") and not alias:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PREVIEW_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID,
                                   value=(field.name,))
        if alias and alias in context:
            dependency_value = context[alias].get(target_field)
            if dependency_value is None and config.get("source_node"):
                dependency_value = f"${{{{{alias}.{target_field}}}}}"
            dependency_nodes.append(cls.build_dependency_tree(
                template=None,
                entity=None,
                alias=alias,
                action="reuse",
                field=field.name,
                target_field=target_field,
                strategy=strategy,
                value=dependency_value,
                message="运行时复用已落库节点字段" if config.get("source_node") else "复用上下文已有数据",
                fields=[],
                missing_fields=[],
            ))
            return dependency_value

        dependency_template = cls.get_dependency_template(field, config)
        dependency_alias = alias or dependency_template.name
        if strategy != "create_always" and dependency_alias in context:
            dependency_value = context.get(dependency_alias, {}).get(target_field)
            runtime_context_required = (
                activation_validation and isinstance(dependency_value, str)
                and "${{" in dependency_value and "}}" in dependency_value
            )
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
                "configuration_valid": True,
                "runtime_context_required": runtime_context_required,
                "can_debug_run": not runtime_context_required,
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
            activation_validation=activation_validation,
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

    @classmethod
    def collect_preview_missing_fields(
            cls,
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
            rows.extend(cls.collect_preview_missing_fields(
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
