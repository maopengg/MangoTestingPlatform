import logging
import uuid
from collections.abc import Callable
from contextlib import ExitStack
from time import perf_counter

from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CONFIG_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_INVALID,
    DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_CREATE_FAILED,
    DATA_FACTORY_UNIQUE_VALUE_CONFLICT,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryExecution,
)
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource, is_missing_value
from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast
from src.apps.data_factory.services.execution.execution_metadata import DataFactoryExecutionMetadata
from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService

logger = logging.getLogger(__name__)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行服务


class DataFactoryRunnerPersistenceMixin:
    @classmethod
    @DataFactorySqlExecutionService.source_for('create')
    def insert(
            cls,
            entity,
            database,
            payload: dict,
            before_commit: Callable[[dict], None] | None = None,
            binding=None,
            execution=None,
            template=None,
            alias: str | None = None,
            prepare_payload: Callable[[], dict] | None = None,
            prepare_resources: Callable[[], None] | None = None,
    ) -> dict:
        try:
            from sqlalchemy import insert, select
        except ImportError as error:
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_INVALID) from error

        preparation_started = perf_counter()
        wait_started = DatasourceWaitService.elapsed()
        timing_started = DatasourceTimingService.snapshot()
        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(database)
        audit_handle = None
        try:
            with engine.connect() as connection:
                table, generated_column_kinds = DataFactoryExecutionMetadata.resolve(
                    entity, database, engine, connection=connection)
                primary_columns = list(table.primary_key.columns)
                actual_primary_keys = [column.name for column in primary_columns]
                if len(actual_primary_keys) != 1 or entity.primary_key != actual_primary_keys[0]:
                    actual_text = "、".join(actual_primary_keys) or "未发现主键"
                    raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(
                        getattr(entity, "name", entity.table_name),
                        f"配置清理主键 {entity.primary_key or '未配置'} 与真实主键 {actual_text} 不一致",
                    ))
            # 资源预检可能等待另一种数据源；不能持有 SQL 连接等待 ES/Redis，
            # 否则多个 Case 可相互耗尽连接。结构读取结束后先归还连接。
            if prepare_resources is not None:
                prepare_resources()
            with ExitStack() as transaction_scope:
                connection = transaction_scope.enter_context(engine.connect())
                if prepare_payload is not None or prepare_resources is not None:
                    # 预检可能等待很久；重新读实时 DDL，由执行级签名拒绝期间的结构漂移。
                    table, generated_column_kinds = DataFactoryExecutionMetadata.resolve(
                        entity, database, engine, connection=connection)
                    if [column.name for column in table.primary_key.columns] != [entity.primary_key]:
                        raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                            value=(entity.name, '资源预检后真实主键与模型不一致，已阻止写入'))
                if prepare_payload is not None:
                    payload = prepare_payload()
                statement = insert(table).values(**payload)
                insert_sql, insert_sql_params = cls.compile_insert_sql(statement, engine.dialect)
                # 结构读取可能触发 SQLAlchemy autobegin；只读准备完成后结束它，
                # 业务写入仍有独立事务，失败时不能提交任何业务行。
                if connection.in_transaction():
                    connection.rollback()
                transaction_scope.enter_context(connection.begin())
                from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
                transaction_scope.enter_context(SqlExecutionAuditService.source({
                    'factory_preparation_ms': round((perf_counter() - preparation_started) * 1000, 2),
                    'factory_preparation_wait_ms': round(max(0, DatasourceWaitService.elapsed() - wait_started) * 1000, 2),
                    'factory_preparation_timing_ms': DatasourceTimingService.delta(timing_started),
                }))

                def execute_insert():
                    result = connection.execute(statement)
                    created = dict(payload)
                    payload_fields = set(payload)
                    cls.merge_generated_values(
                        connection=connection,
                        table=table,
                        result=result,
                        created=created,
                        payload_fields=payload_fields,
                        unique_key=str(getattr(entity, "unique_key", "") or ""),
                        select=select,
                        generated_column_kinds=generated_column_kinds,
                    )
                    insert_result = {
                        "created": created,
                        "insert_sql": insert_sql,
                        "insert_sql_params": insert_sql_params,
                    }
                    if before_commit:
                        insert_result["execution_item"] = before_commit(insert_result)
                    return insert_result, {
                        'columns': [],
                        'rows': [],
                        'row_count': 0,
                        'affected_rows': max(int(getattr(result, 'rowcount', 0) or 0), 0),
                    }

                if binding is not None and execution is not None:
                    insert_result, audit_handle = DataFactorySqlExecutionService.execute(
                        connection=connection,
                        statement=statement,
                        binding=binding,
                        execution=execution,
                        stage='create',
                        callback=execute_insert,
                        template=template,
                        entity=entity,
                        alias=alias,
                    )
                    insert_result["sql_execution_id"] = audit_handle.record.id
                else:
                    insert_result, _audit_result = execute_insert()
                return insert_result
        except DataFactoryError as error:
            if audit_handle is not None:
                DataFactorySqlExecutionService.mark_rolled_back([audit_handle], error)
            raise
        except Exception as error:
            if audit_handle is not None:
                DataFactorySqlExecutionService.mark_rolled_back([audit_handle], error)
            from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
            if DataSourceErrorService.server_error_number(error) == 1062:
                from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                failure = DataSourceErrorService.preserve_execution_state(error, DataFactoryError(
                    DATA_FACTORY_UNIQUE_VALUE_CONFLICT, value=(entity.name,)))
                raise DatasourceInfrastructureService.annotate(failure,
                    request_id=getattr(failure, '_datasource_audit_request_id', None)) from error
            raise DataFactoryError(DATA_FACTORY_RUNNER_PARTS_PERSISTENCE_SQL_CREATE_FAILED, value=(error,)) from error
        finally:
            if not managed_by_worker:
                engine.dispose()

    @staticmethod
    def merge_generated_values(
            connection,
            table,
            result,
            created: dict,
            payload_fields: set[str],
            unique_key: str,
            select,
            generated_column_kinds: dict[str, str] | None = None,
    ) -> None:
        from sqlalchemy import DateTime, JSON, UniqueConstraint, bindparam, cast

        primary_columns = list(table.primary_key.columns)
        payload = {name: created[name] for name in payload_fields}
        inserted_primary_key = tuple(result.inserted_primary_key or ())
        primary_values = dict(zip((column.name for column in primary_columns), inserted_primary_key))
        candidates = []
        generated_column_kinds = generated_column_kinds or {}
        auto_columns = [
            column for column in table.columns
            if column.name not in payload_fields and (
                column.name in generated_column_kinds if generated_column_kinds else column.autoincrement is True
            )
        ]
        driver_key_is_unambiguous = len(generated_column_kinds) <= 1 and len(auto_columns) <= 1
        driver_primary_is_reliable = driver_key_is_unambiguous or (
                connection.dialect.name != "mysql" and not generated_column_kinds
        )
        lastrowid = getattr(result, "lastrowid", None)
        unique_index_columns = {
            tuple(column.name for column in index.columns)
            for index in table.indexes
            if index.unique
        }
        unique_index_columns.update(
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
        )
        if (
                (unique_key,) in unique_index_columns
                and unique_key in payload_fields
                and not is_missing_value(payload.get(unique_key))
        ):
            candidates.append((table.c[unique_key], payload[unique_key], True))
        if len(primary_columns) == 1:
            column = primary_columns[0]
            value = payload.get(column.name) if column.name in payload_fields else primary_values.get(column.name)
            if not is_missing_value(value) and (column.name in payload_fields or value != 0):
                candidates.append((column, value, column.name in payload_fields or driver_primary_is_reliable))
        if not is_missing_value(lastrowid) and lastrowid != 0:
            # TiDB's two generation attributes may share one driver return slot. Verify both,
            # rather than assigning lastrowid to an arbitrary reflected column.
            if len(auto_columns) == 1 or generated_column_kinds:
                candidates.extend((column, lastrowid, driver_key_is_unambiguous) for column in auto_columns)

        matches = {}
        tried = set()
        ambiguous = False
        for column, value, reliable_identity in candidates:
            candidate_key = (column.name, value)
            if candidate_key in tried:
                continue
            tried.add(candidate_key)
            rows = connection.execute(select(table).where(column == value).limit(2)).mappings().all()
            logger.debug(
                "Factory generated-key lookup column=%s rows=%s primary_types=%s lastrowid_type=%s kinds=%s",
                column.name, len(rows), [type(item).__name__ for item in inserted_primary_key],
                type(lastrowid).__name__, generated_column_kinds,
            )
            if len(rows) > 1:
                ambiguous = True
            if len(rows) != 1:
                continue
            row = dict(rows[0])
            if any(is_missing_value(row.get(item.name)) for item in primary_columns):
                continue
            # A reliable insert identity survives database rounding and trigger changes.
            # TiDB's ambiguous driver values still require the ownership checks below.
            if reliable_identity:
                created.update(row)
                return
            # Let the database compare typed values (timestamps, JSON, decimals, nulls).
            # A driver-generated number alone must not authorize another execution's row.
            payload_conditions = []
            for name, inserted_value in payload.items():
                payload_column = table.c[name]
                comparison_column = payload_column
                if connection.dialect.name == "mysql" and isinstance(payload_column.type, DateTime):
                    from sqlalchemy.dialects.mysql import DATETIME

                    inserted_value = cast(inserted_value, DATETIME(fsp=getattr(payload_column.type, "fsp", None)))
                elif inserted_value is None and isinstance(payload_column.type,
                                                           JSON) and not payload_column.type.none_as_null:
                    inserted_value = bindparam(None, None, type_=payload_column.type)
                if connection.dialect.name == "postgresql" and isinstance(payload_column.type, JSON):
                    from sqlalchemy.dialects.postgresql import JSONB

                    if not isinstance(payload_column.type, JSONB):
                        comparison_column = cast(payload_column, JSONB)
                        if inserted_value is not None:
                            inserted_value = cast(bindparam(None, payload[name], type_=payload_column.type), JSONB)
                payload_conditions.append(comparison_column == inserted_value)
            belongs_to_insert = connection.execute(select(*primary_columns).where(
                *(item == row[item.name] for item in primary_columns),
                *payload_conditions,
            ).limit(1)).first()
            if belongs_to_insert is None:
                continue
            matches[tuple(row[item.name] for item in primary_columns)] = row

        if not ambiguous and len(matches) == 1:
            created.update(next(iter(matches.values())))
        else:
            for column in primary_columns:
                if column.name not in payload_fields:
                    created.pop(column.name, None)
            logger.warning(
                "Factory generated-key recovery rejected: candidates=%s matched_rows=%s ambiguous=%s kinds=%s",
                len(tried), len(matches), ambiguous, generated_column_kinds,
            )

    @staticmethod
    def cleanup_failed_execution(execution: DataFactoryExecution, create_error: Exception) -> None:
        """场景任一节点创建失败时，立即清理同一 execution 已落库的全部节点。"""
        from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup

        try:
            DataFactoryCleanup.cleanup_execution(
                execution.id,
                force_cleanup=True,
                allow_missing=True,
            )
        except Exception as cleanup_error:
            DataFactoryCleanup.mark_execution_failed(
                execution,
                f"数据创建失败：{create_error}；自动清理失败：{cleanup_error}",
            )

    @staticmethod
    def compile_insert_sql(statement, dialect):
        compiled = statement.compile(dialect=dialect)
        return str(compiled), DataFactoryTypeCast.to_jsonable(dict(compiled.params or {}))

    @staticmethod
    def build_execution_no() -> str:
        return f"DF{uuid.uuid4().hex[:24].upper()}"
