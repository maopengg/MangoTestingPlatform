from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_UNAVAILABLE,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_INVALID,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_SQL_CREATE_INVALID,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_ENTITY_CONFIG_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NODE_INVALID,
    DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryTemplate,
)
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.services.assets.entity import DataFactoryEntityService
from src.apps.data_factory.services.execution.execution_snapshot import DATA_FACTORY_INSERT_SNAPSHOT_KEY, build_insert_snapshot
from src.apps.data_factory.services.execution.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.execution.runtime_cache import DataFactoryRuntimeCache
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务


class DataFactoryRunnerExecutionMixin:
    @classmethod
    @DataFactoryExecutionMetadata.scope()
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
        cls.require_template_entities_available(template, test_object_id)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        with DataFactoryRuntimeCache.bind_context(test_data, context):
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
                context=DataFactoryCleanupScheduleService.execution_context(context),
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
                post_insert_updates = cls.execute_post_insert_updates(
                    template,
                    execution,
                    runtime_context,
                    main_overrides,
                    item_overrides,
                )
                output = cls.build_output(template.output_config, data)
                execution.context = DataFactoryCleanupScheduleService.execution_context(runtime_context)
                execution.status = DataFactoryExecutionStatusEnum.SUCCESS.value
                execution.cleanup_status = cls.resolve_execution_cleanup_status(execution)
                execution.save()
                cls.sync_execution_cleanup_todo(execution)
                result = {
                    "execution_id": execution.id,
                    "execution_no": execution.execution_no,
                    "context": execution.context,
                    "data": data,
                    "output": output,
                    "items": items,
                    "post_insert_updates": post_insert_updates,
                    "items_output": {item["name"]: item.get("output") or item.get("data") for item in items},
                }
            except Exception as error:
                execution.status = DataFactoryExecutionStatusEnum.FAIL.value
                execution.error_message = str(error)
                execution.save()
                cls.cleanup_failed_execution(execution, error)
                raise

            # 调试入口没有 Case 后置负责接棒；自动策略必须在返回前走正式同步清理。
            # 放在创建异常处理之外，清理失败不冒充创建失败，也不再次发送清理请求。
            if execution.cleanup_status == DataFactoryCleanupStatusEnum.NOT_CLEANED.value:
                try:
                    DataFactoryCleanupScheduleService.execute(execution, force_cleanup=False)
                except Exception:
                    from src.common.logging import log
                    try:
                        DataFactoryCleanupScheduleService.record_wait_failure(execution.id)
                    except Exception as persistence_error:
                        log.system.error('独立调试清理失败状态保存未完成，execution_id=%s exception_type=%s',
                                         execution.id, type(persistence_error).__name__)
                    raise
                execution.refresh_from_db(fields=['cleanup_status'])
            result['cleanup_status'] = execution.cleanup_status
            return result

    @classmethod
    @DataFactoryExecutionMetadata.scope()
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
        cls.require_template_entities_available(template, test_object_id)
        test_data = test_data or DataFactoryRuntimeCache.build_test_data(template.project_product_id, test_env)
        with DataFactoryRuntimeCache.bind_context(test_data, context):
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
                context=DataFactoryCleanupScheduleService.execution_context(context),
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
                    root_alias=alias_override,
                )
                post_insert_updates = cls.execute_post_insert_updates(
                    template,
                    execution,
                    runtime_context,
                    main_overrides,
                    item_overrides,
                    root_alias=alias_override,
                )
                output = cls.build_output(template.output_config, data)
                execution.context = DataFactoryCleanupScheduleService.execution_context(runtime_context)
                execution.status = DataFactoryExecutionStatusEnum.SUCCESS.value
                execution.cleanup_status = cls.resolve_execution_cleanup_status(execution)
                execution.save()
                cls.sync_execution_cleanup_todo(execution)
                return {
                    "execution_id": execution.id,
                    "execution_no": execution.execution_no,
                    "context": execution.context,
                    "data": data,
                    "output": output,
                    "items": items,
                    "post_insert_updates": post_insert_updates,
                    "items_output": {item["name"]: item.get("output") or item.get("data") for item in items},
                }
            except Exception as error:
                execution.status = DataFactoryExecutionStatusEnum.FAIL.value
                execution.error_message = str(error)
                execution.save()
                cls.cleanup_failed_execution(execution, error)
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
            root_alias: str | None = None,
    ) -> list[dict]:
        results = []
        for item in cls.get_template_items(template):
            overrides = {
                **(item.field_overrides or {}),
                **cls.get_item_override(item, item_overrides),
            }
            overrides = cls.prepare_scene_item_overrides(
                template,
                item,
                overrides,
                root_alias=root_alias,
            )
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

    @staticmethod
    def cleanup_status_for_strategy(cleanup_strategy: int) -> int:
        if cleanup_strategy == DataFactoryCleanupStrategyEnum.MANUAL.value:
            return DataFactoryCleanupStatusEnum.PENDING_MANUAL.value
        if cleanup_strategy == DataFactoryCleanupStrategyEnum.NONE.value:
            return DataFactoryCleanupStatusEnum.SKIPPED.value
        return DataFactoryCleanupStatusEnum.NOT_CLEANED.value

    @classmethod
    def resolve_execution_cleanup_status(cls, execution: DataFactoryExecution) -> int:
        strategies = set(
            DataFactoryExecutionItem.objects.filter(execution=execution)
            .values_list('cleanup_strategy', flat=True)
        )
        if DataFactoryCleanupStrategyEnum.EXECUTION_END.value in strategies:
            return DataFactoryCleanupStatusEnum.NOT_CLEANED.value
        if DataFactoryCleanupStrategyEnum.MANUAL.value in strategies:
            return DataFactoryCleanupStatusEnum.PENDING_MANUAL.value
        return DataFactoryCleanupStatusEnum.SKIPPED.value

    @staticmethod
    def sync_execution_cleanup_todo(execution: DataFactoryExecution) -> None:
        from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup

        DataFactoryCleanup.sync_workbench_todo(execution)

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
        if template.entity.status != StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_FACTORY_ENTITY_UNAVAILABLE,
                                   value=DataFactoryEntityService.unavailable_error_values(template.entity),
                                   )
        visiting = visiting or set()
        if template.id in visiting:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_INVALID, value=(template.name,))
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
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_SQL_CREATE_INVALID)
        if not entity.table_name:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_ENTITY_CONFIG_REQUIRED, value=(entity.name,))
        binding = DataFactoryDatasourceResolver.resolve_entity_binding(entity, test_object_id)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=True)
        database = DatasourceTargetService.resolve(binding, schema_name=entity.schema_name)

        fields = DataFactoryExecutionMetadata.fields(entity)
        merged_overrides = {**(template.field_overrides or {}), **overrides}
        fields = cls.build_effective_fields(fields, merged_overrides)
        cls.resolve_dependencies(fields, execution, context, test_object_id, visiting, test_data)
        payload = {}
        preflight_payload = {}
        alias = alias_override or template.name

        def prepare_resources():
            from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
            rules = DataFactoryCleanupResourceService.normalize(getattr(template, 'cleanup_resources', []) or [])
            tenant_fields = {rule['tenant_field'] for rule in rules}
            # 预检只需租户；提前冻结它而不提前生成时间字段、随机业务键或再次创建依赖。
            preflight_payload.update(DataFactoryValueGenerator.build_payload(
                [field for field in fields if field.name in tenant_fields], None, context, test_data))
            DataFactoryCleanupResourceService.preflight(template, preflight_payload, binding, execution=execution)

        def prepare_payload():
            payload.update(DataFactoryValueGenerator.build_payload(fields, preflight_payload, context, test_data))
            return payload

        def record_execution_item(insert_result: dict):
            created = insert_result["created"]
            from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
            cleanup_resources = DataFactoryCleanupResourceService.capture(template, entity, created, binding)
            cleanup_strategy = (
                cleanup_strategy_override
                if cleanup_strategy_override is not None
                else template.cleanup_strategy
            )
            primary_value = created.get(entity.primary_key)
            if (
                    cleanup_strategy != DataFactoryCleanupStrategyEnum.NONE.value
                    and is_missing_value(primary_value)
            ):
                raise DataFactoryError(
                    DATA_FACTORY_RUNNER_PARTS_EXECUTION_PRIMARY_KEY_REQUIRED,
                    value=(entity.name, entity.primary_key),
                )
            return DataFactoryExecutionItem.objects.create(
                execution=execution,
                template=template,
                database_id=database.id,
                datasource_binding=binding,
                alias=alias,
                primary_value=str(primary_value or ""),
                data=DataFactoryTypeCast.to_jsonable({**payload, **created}),
                insert_data=DataFactoryTypeCast.to_jsonable(payload),
                insert_sql=None,
                insert_sql_params={
                    DATA_FACTORY_INSERT_SNAPSHOT_KEY: build_insert_snapshot(entity, binding),
                },
                cleanup_strategy=cleanup_strategy,
                cleanup_resources=cleanup_resources,
                cleanup_order=entity.cleanup_order,
                cleanup_status=cls.cleanup_status_for_strategy(cleanup_strategy),
            )

        insert_result = cls.insert(
            entity,
            database,
            payload,
            before_commit=record_execution_item,
            binding=binding,
            execution=execution,
            template=template,
            alias=alias,
            prepare_payload=prepare_payload,
            prepare_resources=prepare_resources,
        )
        created = insert_result["created"]
        jsonable_payload = DataFactoryTypeCast.to_jsonable({**payload, **created})
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
            if config.get("source_node") and not alias:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_SCENARIO_FIELD_CONFIG_NODE_RELATION_INVALID,
                                       value=(field.name,))
            if alias and strategy != "create_always" and alias in context:
                if config.get("source_node") and context[alias].get(config.get("field", "id")) is None:
                    raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NODE_INVALID,
                                           value=(field.name, config['source_node'],
                                                  config.get('source_field') or 'id'))
                continue
            if strategy == "must_exist":
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_EXECUTION_FIELD_NOT_FOUND, value=(field.name, alias))

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
