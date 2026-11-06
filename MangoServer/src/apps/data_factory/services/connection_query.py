import re

import sqlparse
from sqlparse import tokens
from time import perf_counter

from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource import DataFactoryDatasource
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource_discovery import DataSourceDiscoveryService
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.services.type_cast import DataFactoryTypeCast
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.exceptions import DATA_SOURCE_QUERY_READ_ONLY, DATA_SOURCE_QUERY_LIMIT_REQUIRED, \
    TestCenterError
from src.apps.test_center.services.data_source import DataSourceConnectionService


class DataSourceConnectionQueryService:
    @staticmethod
    def validate_sql(sql):
        statements = sqlparse.parse(sql)
        if len(statements) != 1:
            raise TestCenterError(DATA_SOURCE_QUERY_READ_ONLY)
        statement = statements[0]
        significant = [token for token in statement.flatten()
                       if not token.is_whitespace and token.ttype not in tokens.Comment]
        if not significant or significant[0].normalized not in {'SELECT', 'WITH', 'SHOW', 'DESC', 'DESCRIBE'}:
            raise TestCenterError(DATA_SOURCE_QUERY_READ_ONLY)
        if significant[0].normalized == 'WITH' and statement.get_type() != 'SELECT':
            raise TestCenterError(DATA_SOURCE_QUERY_READ_ONLY)
        for token in significant:
            if token.ttype in tokens.Keyword.DML and token.normalized != 'SELECT':
                raise TestCenterError(DATA_SOURCE_QUERY_READ_ONLY)
            if token.ttype in tokens.Keyword and token.normalized in {
                'INTO', 'FOR', 'UPDATE', 'LOCK', 'OUTFILE', 'DUMPFILE',
            }:
                raise TestCenterError(DATA_SOURCE_QUERY_READ_ONLY)
        outer_tokens = list(statement.tokens)
        limit_index = next((index for index, token in enumerate(outer_tokens)
                            if token.ttype in tokens.Keyword and token.normalized == 'LIMIT'), None)
        if limit_index is None:
            raise TestCenterError(DATA_SOURCE_QUERY_LIMIT_REQUIRED)
        limit_tail = ''.join(str(token) for token in outer_tokens[limit_index + 1:]).strip()
        match = re.fullmatch(r'(\d+)(?:\s*,\s*(\d+)|\s+OFFSET\s+\d+)?\s*;?', limit_tail, re.IGNORECASE)
        if not match or not 1 <= int(match.group(2) or match.group(1)) <= 200:
            raise TestCenterError(DATA_SOURCE_QUERY_LIMIT_REQUIRED)
        return str(statement).strip()

    @classmethod
    def query(cls, source_id, database_name, sql, *, operator_id=None):
        source = DataSourceDiscoveryService.get_database(source_id)
        DataSourceDiscoveryService.require_relational(source)
        target = DatasourceTargetService.build(source, database_name=database_name)
        return cls.query_target(target, sql, operator_id=operator_id)

    @classmethod
    def query_binding(cls, alias_id, product_id, environment, sql, *, operator_id=None):
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(alias_id, product_id, environment)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        target = DatasourceTargetService.resolve(binding)
        DataSourceConnectionService.require_sql(target)
        return cls.query_target(target, sql, binding=binding, project_product_id=product_id,
                                test_env=environment, operator_id=operator_id)

    @classmethod
    def query_target(cls, target, sql, *, binding=None, project_product_id=None, test_env=None, operator_id=None):
        sql = cls.validate_sql(sql)
        started = perf_counter()
        audit = SqlExecutionAuditService.start(
            binding=binding, database=target, project_product_id=project_product_id, test_env=test_env, sql=sql,
            parameters=None, request_id=None, started_monotonic=started,
            source_context={'source_type': 'data_source_debug', 'source_stage': 'query',
                            'source_id': binding.datasource_alias_id if binding else target.id,
                            'operator_id': operator_id, 'database_name': target.database_name,
                            'target_kind': 'logical_database' if binding else 'connection'},
        )
        started = perf_counter()
        try:
            with SqlExecutionAuditService.scope(audit):
                result = cls.execute_target(target, sql)
        except Exception as error:
            SqlExecutionAuditService.finish_failure(audit, error, round((perf_counter() - started) * 1000, 2))
            raise
        SqlExecutionAuditService.finish_success(audit, result, round((perf_counter() - started) * 1000, 2))
        return {**result, 'sql_execution_id': audit.record.id}

    @classmethod
    def execute_target(cls, target, sql):
        engine = DataFactoryDatasource.create_engine(target,
                                                     timeout_seconds=DataSourceConnectionService.timeout_seconds())
        try:
            with engine.connect() as connection:
                # 数据库层只读事务拦截 SELECT 函数/CTE 中隐藏的写入，不能只依赖 SQL 前缀。
                connection.exec_driver_sql('PRAGMA query_only=ON' if target.db_type == DataSourceTypeEnum.SQLITE.value
                                           else 'SET TRANSACTION READ ONLY')
                try:
                    result = connection.exec_driver_sql(sql)
                    columns = list(result.keys())
                    rows = result.fetchmany(201)
                    return {'columns': columns,
                            'rows': DataFactoryTypeCast.to_jsonable([list(row) for row in rows[:200]]),
                            'row_count': min(len(rows), 200), 'truncated': len(rows) > 200}
                finally:
                    connection.rollback()
        except Exception as error:
            DataSourceErrorService.raise_sql_error(target, error)
        finally:
            engine.dispose()
