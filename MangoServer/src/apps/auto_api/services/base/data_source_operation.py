from src.apps.auto_api.exceptions import (
    API_DATA_SOURCE_OPERATION_DATABASE_DATA_SOURCE_REQUIRED,
    API_DATA_SOURCE_OPERATION_DATABASE_EXECUTION_REQUIRED,
    API_SQL_ASSERTION_SQL_DATABASE_ASSERTION_EXECUTION_NOT_ALLOWED,
    AutoApiError,
)

from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
from src.common.exceptions import ErrorDefinition


class DataSourceAssertionConnection:
    """让既有 SQL 断言消费统一数据源执行结果，不再持有真实数据库连接。"""

    def __init__(self, execution_result: dict):
        self.rows = execution_result.get('rows') or []

    def condition_execute(self, _operation_config):
        return self.rows


def execute_data_source_operation(
        test_setup,
        test_env: int,
        item: dict,
        *,
        project_product_id: int | None = None,
        source_context: dict | None = None,
) -> dict:
    datasource_alias_id = item.get('datasource_alias')
    if not datasource_alias_id:
        raise AutoApiError(API_DATA_SOURCE_OPERATION_DATABASE_DATA_SOURCE_REQUIRED)
    if project_product_id is None and not test_setup.test_object:
        raise AutoApiError(API_DATA_SOURCE_OPERATION_DATABASE_EXECUTION_REQUIRED)
    resolved_project_product_id = (
        project_product_id
        if project_product_id is not None
        else test_setup.test_object.project_product_id
    )
    operation_config = test_setup.test_data.replace(item.get('value'))
    return DataSourceExecutionService.execute(
        datasource_alias_id=datasource_alias_id,
        project_product_id=resolved_project_product_id,
        test_env=test_env,
        operation_config=operation_config,
        source_context=source_context or {
            'source_type': 'api_runtime',
            'source_stage': 'database_operation',
        },
    )


def execute_data_source_query(
        test_setup,
        test_env: int,
        item: dict,
        *,
        write_error: ErrorDefinition,
        operation_name: str = 'SQL查询语句',
        source_context: dict | None = None,
) -> dict:
    operation_config = test_setup.test_data.replace(item.get('value'))
    sql = DataSourceExecutionService.normalize_text_operation(
        operation_config,
        operation_name,
    )
    if not DataSourceExecutionService.is_sql_query(sql):
        raise AutoApiError(write_error)
    return execute_data_source_operation(
        test_setup,
        test_env,
        {**item, 'value': sql},
        source_context=source_context,
    )


def execute_data_source_assertion(
        test_setup,
        test_env: int,
        item: dict,
        *,
        source_context: dict | None = None,
) -> dict:
    return execute_data_source_query(
        test_setup,
        test_env,
        item,
        write_error=API_SQL_ASSERTION_SQL_DATABASE_ASSERTION_EXECUTION_NOT_ALLOWED,
        operation_name='SQL断言语句',
        source_context=source_context,
    )


def cache_data_source_result(test_setup, key: str, execution_result: dict) -> bool:
    cache_record = DataSourceExecutionService.cache_record(key, execution_result)
    if not cache_record:
        return False
    test_setup.test_data.set_sql_cache(key, cache_record)
    return True
