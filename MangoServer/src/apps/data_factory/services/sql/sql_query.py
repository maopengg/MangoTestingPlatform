from mangotools.database import SqlPermissionGuard

from src.apps.data_factory.exceptions import (
    DataFactoryError,
    DATA_SOURCE_SQL_REQUIRED,
    DATA_SOURCE_SINGLE_SQL_REQUIRED,
    DATA_SOURCE_QUERY_ONLY,
    DATA_SOURCE_SQLALCHEMY_REQUIRED,
)
from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.test_center.services.datasource.database_connection import DatabaseConnection


class DataFactorySqlQuery:
    @staticmethod
    def query(database: Database, sql: str, limit: int = 100, allow_query: bool = False) -> dict:
        sql = (sql or "").strip()
        if not sql:
            raise DataFactoryError(DATA_SOURCE_SQL_REQUIRED)
        if ';' in sql.rstrip(';'):
            raise DataFactoryError(DATA_SOURCE_SINGLE_SQL_REQUIRED)
        if not SqlPermissionGuard.is_query(sql):
            raise DataFactoryError(DATA_SOURCE_QUERY_ONLY)
        SqlPermissionGuard.check(
            sql,
            allow_query=allow_query,
            allow_write=False,
        )
        from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
        DatasourceCostService.sql(sql)

        try:
            from sqlalchemy import text
        except ImportError as error:
            raise DataFactoryError(DATA_SOURCE_SQLALCHEMY_REQUIRED) from error

        max_rows = max(1, int(limit or 100))
        engine = None
        try:
            engine = DataFactoryDatasource.create_engine(database)
            with engine.connect() as connection:
                connection = connection.execution_options(stream_results=True)
                result = connection.execute(text(sql))
                if not result.returns_rows:
                    return {
                        "columns": [],
                        "rows": [],
                        "row_count": 0,
                        "truncated": False,
                    }
                rows = [
                    DatabaseConnection.convert_datetime_to_string(dict(row._mapping))
                    for row in result.fetchmany(max_rows + 1)
                ]
                truncated = len(rows) > max_rows
                if truncated:
                    DatasourceCostService.abort_result(connection, result, limit=max_rows, observed_rows=len(rows))
                return {
                    "columns": list(result.keys()),
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": truncated,
                }
        except DataFactoryError:
            raise
        except Exception as error:
            DataSourceErrorService.raise_sql_error(database, error)
        finally:
            if engine:
                engine.dispose()
