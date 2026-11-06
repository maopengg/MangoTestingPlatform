import sqlparse
from mangotools.exceptions import MangoToolsError
from sqlparse.tokens import DML
from time import perf_counter

from src.apps.data_factory.exceptions import (
    DATA_SOURCE_OPERATION_REQUIRED,
    DATA_SOURCE_OPERATION_PARAMETER_INVALID,
    DATA_SOURCE_OPERATION_DATA_SOURCE_TYPE_EXECUTION_UNSUPPORTED,
    DATA_SOURCE_OPERATION_DATABASE_EXECUTION_FAILED,
    DATA_SOURCE_OPERATION_INVALID,
    DATA_SOURCE_OPERATION_INVALID_CODE_INVALID,
    DATA_SOURCE_OPERATION_EXECUTION_INVALID,
    DATA_SOURCE_OPERATION_JSON_EXECUTION_INVALID,
    DATA_SOURCE_OPERATION_EXECUTION_INVALID_CODE_EXECUTION_INVALID,
    DATA_SOURCE_OPERATION_NAME_REQUIRED,
    DATA_SOURCE_OPERATION_JSON_INVALID,
    DATA_SOURCE_OPERATION_SQL_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.data_source_query import DataFactoryDatasourceQuery
from src.apps.data_factory.services.datasource import (
    DataFactoryDatasource,
    DataFactoryDatasourceResolver,
)
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.services.database_connection import DatabaseConnection
from src.common.exceptions import MangoServerError


class DataSourceExecutionService:
    MAX_OPERATION_LENGTH = 100_000

    @classmethod
    def max_rows(cls) -> int:
        from src.apps.system.services.system_config import SystemConfigService

        return SystemConfigService.get_ranged_int('DATA_QUERY_MAX_ROWS')

    RELATIONAL_TYPES = {
        DataSourceTypeEnum.MYSQL.value,
        DataSourceTypeEnum.POSTGRESQL.value,
        DataSourceTypeEnum.SQLITE.value,
        DataSourceTypeEnum.ORACLE.value,
        DataSourceTypeEnum.SQLSERVER.value,
    }
    EXECUTABLE_RELATIONAL_TYPES = {
        DataSourceTypeEnum.MYSQL.value,
        DataSourceTypeEnum.POSTGRESQL.value,
        DataSourceTypeEnum.SQLITE.value,
    }
    SQL_READ_TYPES = {'SELECT'}
    SQL_READ_PREFIXES = ('SHOW', 'DESC', 'DESCRIBE')

    @classmethod
    def execute(
            cls,
            *,
            datasource_alias_id,
            project_product_id,
            test_env,
            operation_config,
            parameters: dict | None = None,
            source_context: dict | None = None,
            request_id: str | None = None,
    ) -> dict:
        datasource_alias_id = cls.normalize_id(datasource_alias_id, '逻辑数据源')
        project_product_id = cls.normalize_id(project_product_id, '项目产品')
        test_env = cls.normalize_id(test_env, '执行环境')
        try:
            binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
                datasource_alias_id,
                project_product_id,
                test_env,
            )
            db_type = binding.database.db_type
            supported_types = cls.EXECUTABLE_RELATIONAL_TYPES | {
                DataSourceTypeEnum.REDIS.value,
                DataSourceTypeEnum.ELASTICSEARCH.value,
            }
            if db_type not in supported_types:
                type_name = DataSourceTypeEnum.obj().get(db_type, db_type)
                raise DataFactoryError(DATA_SOURCE_OPERATION_DATA_SOURCE_TYPE_EXECUTION_UNSUPPORTED, value=(type_name,))
            is_write = cls.is_write_operation(db_type, operation_config)
            DataFactoryDatasourceResolver.require_binding_permission(binding, write=is_write)
            started_at = perf_counter()
            from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
            audit_handle = SqlExecutionAuditService.start(
                binding=binding,
                database=DatasourceTargetService.resolve(binding),
                project_product_id=project_product_id,
                test_env=test_env,
                sql=operation_config,
                parameters=parameters,
                source_context=source_context or {
                    'source_type': 'data_source_runtime',
                    'source_stage': 'execute',
                    'source_id': datasource_alias_id,
                },
                request_id=request_id,
                started_monotonic=started_at,
            )
            if audit_handle.existing:
                return SqlExecutionAuditService.replay_result(audit_handle)
            started_at = perf_counter()
            try:
                with SqlExecutionAuditService.scope(audit_handle):
                    result = cls.execute_backend(binding, operation_config, is_write, parameters)
            except Exception as error:
                SqlExecutionAuditService.finish_failure(
                    audit_handle, error, round((perf_counter() - started_at) * 1000, 2),
                )
                raise
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            SqlExecutionAuditService.finish_success(audit_handle, result, duration_ms)
            duration_ms = audit_handle.record.duration_ms
            return {
                **result,
                'datasource_alias_id': binding.datasource_alias_id,
                'datasource_type': db_type,
                'test_env': test_env,
                'duration_ms': duration_ms,
                'sql_execution_id': audit_handle.record.id,
                'is_slow': audit_handle.record.is_slow,
            }
        except (MangoServerError, MangoToolsError):
            raise
        except Exception as error:
            safe_message = DataFactoryDatasource._safe_error(
                DatasourceTargetService.resolve(binding),
                error,
            ) if 'binding' in locals() else str(error)
            raise DataFactoryError(DATA_SOURCE_OPERATION_DATABASE_EXECUTION_FAILED, value=(safe_message,)) from error

    @classmethod
    def execute_backend(cls, binding, operation_config, is_write, parameters):
        db_type = binding.database.db_type
        if db_type in cls.EXECUTABLE_RELATIONAL_TYPES:
            result = cls.execute_sql(
                DatasourceTargetService.resolve(binding), operation_config,
                is_write=is_write, parameters=parameters,
            )
        elif db_type == DataSourceTypeEnum.REDIS.value:
            result = DataFactoryDatasourceQuery.execute_redis(
                DatasourceTargetService.resolve(binding), operation_config,
                allow_query=True, allow_write=True,
            )
        elif db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            result = cls.execute_elasticsearch(DatasourceTargetService.resolve(binding), operation_config)
        else:
            type_name = DataSourceTypeEnum.obj().get(db_type, db_type)
            raise DataFactoryError(DATA_SOURCE_OPERATION_DATA_SOURCE_TYPE_EXECUTION_UNSUPPORTED, value=(type_name,))
        return result

    @staticmethod
    def normalize_id(value, name: str) -> int:
        if value in [None, '']:
            raise DataFactoryError(DATA_SOURCE_OPERATION_REQUIRED, value=(name,))
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise DataFactoryError(DATA_SOURCE_OPERATION_PARAMETER_INVALID, value=(name,)) from error

    @classmethod
    def is_write_operation(cls, db_type: int, operation_config) -> bool:
        if db_type in cls.RELATIONAL_TYPES:
            sql = cls.normalize_text_operation(operation_config, 'SQL语句')
            return not cls.is_sql_query(sql)
        if db_type == DataSourceTypeEnum.REDIS.value:
            command = cls.normalize_text_operation(operation_config, 'Redis命令')
            command_name = DataFactoryDatasourceQuery.redis_command_name(command)
            return command_name not in DataFactoryDatasourceQuery.REDIS_READ_COMMANDS
        if db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            cls.normalize_elasticsearch_config(operation_config)
            return False
        type_name = DataSourceTypeEnum.obj().get(db_type, db_type)
        raise DataFactoryError(DATA_SOURCE_OPERATION_DATA_SOURCE_TYPE_EXECUTION_UNSUPPORTED, value=(type_name,))

    @classmethod
    def execute_sql(
            cls,
            database,
            operation_config,
            *,
            is_write: bool,
            parameters: dict | None = None,
    ) -> dict:
        sql = cls.normalize_text_operation(operation_config, 'SQL语句')
        from src.apps.data_factory.services.datasource_cost import DatasourceCostService
        DatasourceCostService.sql(sql)
        try:
            from sqlalchemy import text
        except ImportError as error:
            raise DataFactoryError(DATA_SOURCE_OPERATION_SQL_REQUIRED) from error

        engine = None
        try:
            engine = DataFactoryDatasource.create_engine(database)
            context = engine.begin() if is_write else engine.connect()
            with context as connection:
                if not is_write:
                    connection = connection.execution_options(stream_results=True)
                result = (
                    connection.execute(text(sql), parameters)
                    if parameters
                    else connection.execute(text(sql))
                )
                columns = list(result.keys()) if result.returns_rows else []
                rows = []
                truncated = False
                if result.returns_rows:
                    max_rows = cls.max_rows()
                    rows = [
                        DatabaseConnection.convert_datetime_to_string(dict(row._mapping))
                        for row in result.fetchmany(max_rows + 1)
                    ]
                    truncated = len(rows) > max_rows
                    if truncated:
                        DatasourceCostService.abort_result(connection, result, limit=max_rows,
                                                          observed_rows=len(rows), is_write=is_write)
                # MySQL 流式查询的 rowcount 可能是 UINT64_MAX（未知），不是影响行数。
                affected_rows = (
                    result.rowcount
                    if not result.returns_rows and result.rowcount is not None and result.rowcount >= 0
                    else 0
                )
            return {
                'execution_type': 'write' if is_write else 'query',
                'columns': columns,
                'rows': rows,
                'result': rows,
                'row_count': len(rows),
                'affected_rows': affected_rows,
                'truncated': truncated,
            }
        except (MangoServerError, MangoToolsError):
            raise
        except Exception as error:
            DataSourceErrorService.raise_sql_error(database, error)
        finally:
            if engine:
                engine.dispose()

    @classmethod
    def execute_elasticsearch(cls, database, operation_config) -> dict:
        config = cls.normalize_elasticsearch_config(operation_config)
        result = DataFactoryDatasourceQuery.query_elasticsearch(
            database,
            config['index'],
            config['query'],
        )
        return {
            **result,
            'execution_type': 'query',
            'rows': cls.elasticsearch_hits(result.get('result')),
            'affected_rows': 0,
        }

    @classmethod
    def normalize_text_operation(cls, value, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise DataFactoryError(DATA_SOURCE_OPERATION_INVALID, value=(name,))
        value = value.strip()
        if len(value) > cls.MAX_OPERATION_LENGTH:
            raise DataFactoryError(DATA_SOURCE_OPERATION_INVALID_CODE_INVALID, value=(name,))
        statement_without_trailing_semicolon = value.rstrip().rstrip(';').rstrip()
        if ';' in statement_without_trailing_semicolon:
            raise DataFactoryError(DATA_SOURCE_OPERATION_EXECUTION_INVALID, value=(name,))
        return value

    @classmethod
    def normalize_elasticsearch_config(cls, value) -> dict:
        if not isinstance(value, dict):
            raise DataFactoryError(DATA_SOURCE_OPERATION_JSON_EXECUTION_INVALID)
        if set(value) != {'index', 'query'}:
            raise DataFactoryError(DATA_SOURCE_OPERATION_EXECUTION_INVALID_CODE_EXECUTION_INVALID)
        index = value.get('index')
        query = value.get('query')
        if not isinstance(index, str) or not index.strip():
            raise DataFactoryError(DATA_SOURCE_OPERATION_NAME_REQUIRED)
        if not isinstance(query, dict):
            raise DataFactoryError(DATA_SOURCE_OPERATION_JSON_INVALID)
        return {'index': index.strip(), 'query': query}

    @classmethod
    def is_sql_query(cls, sql: str) -> bool:
        parsed = sqlparse.parse(sql)
        if len(parsed) != 1:
            raise DataFactoryError(DATA_SOURCE_OPERATION_EXECUTION_INVALID, value=('SQL',))
        operation = next(
            (
                token.normalized.upper()
                for token in parsed[0].tokens
                if token.ttype is DML
            ),
            parsed[0].get_type().upper(),
        )
        return operation in cls.SQL_READ_TYPES or sql.lstrip().upper().startswith(
            cls.SQL_READ_PREFIXES
        )

    @staticmethod
    def redis_result_record(key: str, result) -> dict | None:
        if not key:
            return None
        keys = [item.strip() for item in key.split(',') if item.strip()]
        if isinstance(result, dict):
            return result
        if isinstance(result, (list, tuple)):
            return {name: value for name, value in zip(keys, result)}
        return {keys[0]: result} if keys else None

    @staticmethod
    def elasticsearch_hits(result) -> list[dict]:
        if not isinstance(result, dict):
            return []
        hits = result.get('hits', {}).get('hits', [])
        return hits if isinstance(hits, list) else []

    @classmethod
    def cache_record(cls, key: str, execution_result: dict) -> dict | None:
        db_type = execution_result.get('datasource_type')
        if db_type in cls.RELATIONAL_TYPES:
            rows = execution_result.get('rows') or []
            return rows[0] if rows and isinstance(rows[0], dict) else None
        if db_type == DataSourceTypeEnum.REDIS.value:
            redis_result = execution_result.get('result')
            if execution_result.get('command') == 'HGETALL' and isinstance(redis_result, list):
                redis_result = dict(zip(redis_result[::2], redis_result[1::2]))
            return cls.redis_result_record(key, redis_result)
        if db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            rows = execution_result.get('rows') or []
            if not rows:
                return None
            first = rows[0]
            if not isinstance(first, dict):
                return None
            source = first.get('_source')
            return source if isinstance(source, dict) else first
        return None
