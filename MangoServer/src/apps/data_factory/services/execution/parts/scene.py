from pydantic import ValidationError

from src.apps.data_factory.enums import (
    DataFactoryGeneratorTypeEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_WRITEBACK_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_RELATION_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND_CODE_FIELD_NODE_NOT_FOUND,
    DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_WRITEBACK_NOT_ALLOWED,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_GENERATE_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_CONFIG_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_SCENE_DATABASE_NODE_BINDING_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_WRITEBACK_DUPLICATED,
    DATA_FACTORY_RUNNER_PARTS_SCENE_SCENARIO_NODE_CREATE_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_GENERATE_WRITEBACK_REQUIRED,
    DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_INVALID,
    DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_WRITEBACK_FAILED,
    DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID_CODE_WRITEBACK_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryExecution,
    DataFactoryExecutionItem,
    DataFactoryTemplate,
)
from src.apps.data_factory.schemas.configuration import (
    DataFactoryFieldOverrideRule,
    DataFactoryFieldOverrideRules,
    DataFactoryOutputConfig,
    DataFactoryPostInsertUpdates,
)
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.execution.execution_snapshot import get_insert_snapshot
from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务


class DataFactoryRunnerSceneMixin:
    @staticmethod
    def parse_field_override_rules(overrides: dict | None) -> dict[str, DataFactoryFieldOverrideRule]:
        if not overrides:
            return {}
        try:
            return DataFactoryFieldOverrideRules.model_validate(overrides).to_dict()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_INVALID, value=(error,)) from error

    @staticmethod
    def build_output(output_config: list | None, payload: dict) -> dict:
        if not output_config:
            return {}
        try:
            items = DataFactoryOutputConfig.model_validate(output_config).to_list()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_INVALID, value=(error,)) from error

        output = {}
        for item in items:
            output[item.key] = payload.get(item.field)
        return output

    @classmethod
    def build_scene_node_registry(
            cls,
            template: DataFactoryTemplate,
            main_overrides: dict | None = None,
            item_overrides: dict | None = None,
    ) -> list[dict]:
        nodes = [{
            "node": "root",
            "alias": template.name,
            "template": template,
            "entity": template.entity,
            "overrides": {**(template.field_overrides or {}), **(main_overrides or {})},
            "item": None,
        }]
        for item in cls.get_template_items(template):
            nodes.append({
                "node": f"item:{item.id}",
                "aliases": [
                    f"item:{item.id}",
                    f"item:{item.name}",
                    item.name,
                    str(item.child_template_id),
                    item.child_template.name,
                ],
                "alias": item.name or item.child_template.name,
                "template": item.child_template,
                "entity": item.child_template.entity,
                "overrides": {
                    **(item.child_template.field_overrides or {}),
                    **(item.field_overrides or {}),
                    **cls.get_item_override(item, item_overrides),
                },
                "item": item,
            })
        return nodes

    @staticmethod
    def resolve_scene_node(nodes: list[dict], reference: str) -> dict:
        if reference == "root":
            return nodes[0]
        matches = [
            node for node in nodes[1:]
            if reference == node["node"] or reference in node.get("aliases", [])
        ]
        if not matches:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_WRITEBACK_NOT_FOUND, value=(reference,))
        if len(matches) > 1:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_RELATION_WRITEBACK_INVALID, value=(reference,))
        return matches[0]

    @classmethod
    def build_post_insert_update_plan(
            cls,
            template: DataFactoryTemplate,
            config: list | None,
            main_overrides: dict | None = None,
            item_overrides: dict | None = None,
    ) -> list[dict]:
        try:
            updates = DataFactoryPostInsertUpdates.model_validate(config or []).to_list()
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_CONFIG_WRITEBACK_INVALID, value=(error,)) from error
        nodes = cls.build_scene_node_registry(template, main_overrides, item_overrides)
        plan = []
        targets = set()
        for update_config in sorted(updates, key=lambda item: item.sort):
            target = cls.resolve_scene_node(nodes, update_config.target_node)
            source = cls.resolve_scene_node(nodes, update_config.source_node)
            target_fields = list(target["entity"].datafactoryfield_set.all().order_by('sort', 'id'))
            source_fields = list(source["entity"].datafactoryfield_set.all().order_by('sort', 'id'))
            target_field_map = {
                item.name: item for item in cls.build_effective_fields(target_fields, target["overrides"])
            }
            source_field_map = {item.name: item for item in source_fields}
            target_field = target_field_map.get(update_config.target_field)
            source_field = source_field_map.get(update_config.source_field)
            if not target_field:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND,
                                       value=(update_config.target_node, update_config.target_field))
            if not source_field:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_NODE_NOT_FOUND_CODE_FIELD_NODE_NOT_FOUND,
                                       value=(update_config.source_node, update_config.source_field))
            if update_config.target_field == target["entity"].primary_key:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_WRITEBACK_NOT_ALLOWED)
            if target_field.generator_type != DataFactoryGeneratorTypeEnum.SKIP.value:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_GENERATE_INVALID,
                                       value=(update_config.target_field,))
            if not target_field.nullable:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_WRITEBACK_INVALID,
                                       value=(update_config.target_field,))
            if not target["entity"].primary_key:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_ENTITY_CONFIG_REQUIRED,
                                       value=(target['entity'].name,))
            if target["entity"].datasource_alias_id != source["entity"].datasource_alias_id:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_DATABASE_NODE_BINDING_WRITEBACK_INVALID)
            target_key = (target["node"], update_config.target_field)
            if target_key in targets:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_FIELD_CONFIG_WRITEBACK_DUPLICATED,
                                       value=(update_config.target_field,))
            targets.add(target_key)
            plan.append({
                **update_config.model_dump(),
                "target_alias": target["alias"],
                "target_template_id": target["template"].id,
                "target_entity": target["entity"],
                "source_alias": source["alias"],
                "source_template_id": source["template"].id,
                "source_entity": source["entity"],
                "sql_template": (
                    f"UPDATE {target['entity'].table_name} SET {update_config.target_field} = :source_value "
                    f"WHERE {target['entity'].primary_key} = :target_primary_key"
                ),
            })
        return plan

    @classmethod
    def preview_post_insert_updates(
            cls,
            template: DataFactoryTemplate,
            config: list | None,
            main_overrides: dict | None = None,
            item_overrides: dict | None = None,
    ) -> list[dict]:
        if not config:
            return []
        try:
            plan = cls.build_post_insert_update_plan(template, config, main_overrides, item_overrides)
            return [{
                        key: value for key, value in item.items()
                        if key not in {"target_entity", "source_entity"}
                    } | {"valid": True, "message": ""} for item in plan]
        except DataFactoryError as error:
            try:
                invalid_items = DataFactoryPostInsertUpdates.model_validate(config or []).model_dump()
            except ValidationError:
                invalid_items = [{}]
            return [
                {**item, "valid": False, "message": str(error)}
                for item in invalid_items
            ]

    @classmethod
    def execute_post_insert_updates(
            cls,
            template: DataFactoryTemplate,
            execution: DataFactoryExecution,
            context: dict,
            main_overrides: dict | None = None,
            item_overrides: dict | None = None,
            root_alias: str | None = None,
    ) -> list[dict]:
        plan = cls.build_post_insert_update_plan(
            template,
            template.post_insert_updates,
            main_overrides,
            item_overrides,
        )
        results = []
        for item in plan:
            target_alias = root_alias if item["target_node"] == "root" and root_alias else item["target_alias"]
            source_alias = root_alias if item["source_node"] == "root" and root_alias else item["source_alias"]
            target_execution_item = DataFactoryExecutionItem.objects.select_related(
                'execution',
                'template__entity',
                'datasource_binding',
            ).filter(
                execution=execution,
                template_id=item["target_template_id"],
                alias=target_alias,
            ).order_by('-id').first()
            source_execution_item = DataFactoryExecutionItem.objects.select_related(
                'execution',
                'template__entity',
                'datasource_binding',
            ).filter(
                execution=execution,
                template_id=item["source_template_id"],
                alias=source_alias,
            ).order_by('-id').first()
            if not target_execution_item or not source_execution_item:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_SCENARIO_NODE_CREATE_WRITEBACK_INVALID)
            source_value = (source_execution_item.data or {}).get(item["source_field"])
            if source_value is None:
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID,
                                       value=(source_alias, item['source_field']))
            target_primary_key = (target_execution_item.data or {}).get(item["target_entity"].primary_key)
            if target_primary_key in (None, ""):
                raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_NODE_GENERATE_WRITEBACK_REQUIRED,
                                       value=(target_alias,))
            audit = {
                "sort": item["sort"],
                "target_node": item["target_node"],
                "target_alias": target_alias,
                "target_field": item["target_field"],
                "source_node": item["source_node"],
                "source_alias": source_alias,
                "source_field": item["source_field"],
                "sql_execution_id": None,
                "affected_rows": 0,
                "status": "failed",
                "error": "",
            }
            try:
                affected_rows, sql_execution_id = cls.update_created_record(
                    item["target_entity"],
                    DatasourceTargetService.from_snapshot(target_execution_item.database,
                                                          get_insert_snapshot(target_execution_item)),
                    item["target_field"],
                    source_value,
                    target_primary_key,
                    execution_item=target_execution_item,
                    return_audit=True,
                )
                if affected_rows != 1:
                    raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_WRITEBACK_INVALID_CODE_WRITEBACK_INVALID,
                                           value=(affected_rows,))
                audit["affected_rows"] = affected_rows
                audit["sql_execution_id"] = sql_execution_id
                audit["status"] = "success"
                target_data = dict(target_execution_item.data or {})
                target_data[item["target_field"]] = DataFactoryTypeCast.to_jsonable(source_value)
                target_execution_item.data = target_data
                context.setdefault(target_alias, {})[item["target_field"]] = DataFactoryTypeCast.to_jsonable(
                    source_value)
                results.append(audit)
            except Exception as error:
                audit["error"] = str(error)
                raise
            finally:
                records = list(target_execution_item.post_update_records or [])
                records.append(audit)
                target_execution_item.post_update_records = records
                target_execution_item.save(update_fields=["data", "post_update_records", "update_time"])
        return results

    @classmethod
    @DataFactorySqlExecutionService.source_for('post_insert_update')
    def update_created_record(
            cls,
            entity,
            database,
            field_name: str,
            value,
            primary_value,
            execution_item=None,
            return_audit: bool = False,
    ):
        try:
            from sqlalchemy import MetaData, Table, update
        except ImportError as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_INVALID) from error
        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(database)
        audit_handle = None
        try:
            snapshot = get_insert_snapshot(execution_item) if execution_item is not None else {}
            table_name = snapshot['table_name'] if execution_item is not None else entity.table_name
            primary_key = snapshot['primary_key'] if execution_item is not None else entity.primary_key
            table = Table(table_name, MetaData(), schema=database.schema_name or None, autoload_with=engine)
            statement = update(table).where(table.c[primary_key] == primary_value).values({field_name: value})
            with engine.begin() as connection:
                if execution_item is None:
                    affected_rows = connection.execute(statement).rowcount
                    return (affected_rows, None) if return_audit else affected_rows

                def execute_update():
                    affected = connection.execute(statement).rowcount
                    return affected, {
                        'columns': [],
                        'rows': [],
                        'row_count': 0,
                        'affected_rows': affected,
                    }

                affected_rows, audit_handle = DataFactorySqlExecutionService.execute(
                    connection=connection,
                    statement=statement,
                    binding=execution_item.datasource_binding,
                    execution=execution_item.execution,
                    stage='post_insert_update',
                    callback=execute_update,
                    item=execution_item,
                    template=execution_item.template,
                    entity=entity,
                )
                if return_audit:
                    return affected_rows, audit_handle.record.id
                return affected_rows
        except Exception as error:
            if audit_handle is not None:
                DataFactorySqlExecutionService.mark_rolled_back([audit_handle], error)
            if isinstance(error, DataFactoryError):
                raise
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_SCENE_SQL_WRITEBACK_FAILED, value=(error,)) from error
        finally:
            if not managed_by_worker:
                engine.dispose()

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
