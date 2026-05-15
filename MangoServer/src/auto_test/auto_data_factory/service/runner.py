# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务

import copy
import uuid

from django.db import transaction
from pydantic import ValidationError

from src.auto_test.auto_data_factory.models import (
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryTemplate,
)
from src.enums.data_factory_enum import (
    DataFactoryCleanupStatusEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
)
from src.exceptions import ToolsError
from src.models.data_factory_model import (
    DataFactoryFieldOverrideRule,
    DataFactoryFieldOverrideRules,
    DataFactoryOutputConfig,
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
        return cls.preview_by_template(
            template,
            overrides or {},
            runtime_context,
            test_object_id,
            set(),
            output_config=output_config,
            test_data=test_data,
        )

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

        fields = list(entity.datafactoryfield_set.all().order_by('sort', 'id'))
        merged_overrides = {**(template.field_overrides or {}), **overrides}
        fields = cls.build_effective_fields(fields, merged_overrides)
        payload = {}
        field_items = []
        missing_fields = []
        dependencies = []
        dependency_nodes = []
        alias = alias_override or template.name

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
        dependency_tree = cls.build_dependency_tree(
            template=template,
            entity=entity,
            alias=alias,
            action="root",
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
        template_id = config.get("template_id")
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
            ))
            return context[alias].get(target_field)
        if not template_id:
            raise ToolsError(300, "依赖字段未配置依赖模板 template_id")

        dependency_template = DataFactoryTemplate.objects.select_related(
            'entity',
            'project_product',
            'entity__datasource_alias',
        ).get(id=template_id)
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
    ) -> dict:
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
                overrides or {},
                runtime_context,
                test_object_id,
                test_data=test_data,
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
        execution = DataFactoryExecution.objects.create(
            execution_no=cls.build_execution_no(),
            source_type=source_type,
            source_id=source_id,
            template=template,
            project_product=template.project_product,
            stage=stage,
            status=DataFactoryExecutionStatusEnum.PROCEED.value,
            context=context or {},
        )

        try:
            runtime_context = context or {}
            data = cls.create_by_template(
                template,
                execution,
                overrides or {},
                runtime_context,
                test_object_id,
                alias_override=alias_override,
                cleanup_strategy_override=cleanup_strategy_override,
                test_data=test_data,
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
            }
        except Exception as error:
            execution.status = DataFactoryExecutionStatusEnum.FAIL.value
            execution.error_message = str(error)
            execution.save()
            raise

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

        fields = list(entity.datafactoryfield_set.all().order_by('sort', 'id'))
        merged_overrides = {**(template.field_overrides or {}), **overrides}
        fields = cls.build_effective_fields(fields, merged_overrides)
        cls.resolve_dependencies(fields, execution, context, test_object_id, visiting, test_data)
        payload = DataFactoryValueGenerator.build_payload(fields, None, context, test_data)
        created = cls.insert(entity, database, payload)
        jsonable_payload = DataFactoryTypeCast.to_jsonable({**payload, **created})
        alias = alias_override or template.name

        DataFactoryExecutionItem.objects.create(
            execution=execution,
            template=template,
            database=database,
            alias=alias,
            primary_value=str(created.get(entity.primary_key) or ""),
            data=jsonable_payload,
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

            template_id = config.get("template_id")
            if not template_id:
                raise ToolsError(300, f"字段 {field.name} 未配置依赖模板 template_id")

            dependency_template = DataFactoryTemplate.objects.select_related(
                'entity',
                'project_product',
                'entity__datasource_alias',
            ).get(id=template_id)
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

        engine = DataFactoryDatasource.create_engine(database)
        try:
            metadata = MetaData()
            table = Table(entity.table_name, metadata, autoload_with=engine)
            with engine.begin() as connection:
                result = connection.execute(insert(table).values(**payload))
                created = dict(payload)
                if result.inserted_primary_key and entity.primary_key:
                    created[entity.primary_key] = result.inserted_primary_key[0]
                return created
        except Exception as error:
            raise ToolsError(300, f"SQL创建数据失败：{error}") from error
        finally:
            engine.dispose()

    @staticmethod
    def build_execution_no() -> str:
        return f"DF{uuid.uuid4().hex[:24].upper()}"
