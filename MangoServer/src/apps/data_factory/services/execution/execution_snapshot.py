# -*- coding: utf-8 -*-

DATA_FACTORY_INSERT_SNAPSHOT_KEY = "__mango_data_factory_snapshot__"


def build_insert_snapshot(entity, binding) -> dict:
    from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
    target = DatasourceTargetService.resolve(binding, schema_name=entity.schema_name)
    return {
        "version": 2,
        "connection_version": target.update_time.isoformat(),
        "database_name": target.database_name,
        "schema_name": target.schema_name,
        "redis_db": target.redis_db,
        "entity_id": entity.id,
        "datasource_alias_id": entity.datasource_alias_id,
        "datasource_binding_id": binding.id,
        "environment": binding.environment,
        "database_id": binding.database_id,
        "table_name": entity.table_name,
        "primary_key": entity.primary_key,
    }


def get_insert_snapshot(item) -> dict:
    raw_params = getattr(item, "insert_sql_params", None)
    params = raw_params if isinstance(raw_params, dict) else {}
    snapshot = params.get(DATA_FACTORY_INSERT_SNAPSHOT_KEY)
    return snapshot if isinstance(snapshot, dict) else {}
