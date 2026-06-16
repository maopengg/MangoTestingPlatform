from src.apps.data_factory.service.datasource import DataFactoryDatasource
from src.apps.system.models import Database
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import ERROR_MSG_0073, ERROR_MSG_0074, ERROR_MSG_0075, ERROR_MSG_0076, ToolsError
from src.common.tools.database import DatabaseConnection, SqlPermissionGuard


class DataFactorySqlQuery:
    @staticmethod
    def query(database: Database, sql: str, limit: int = 100) -> dict:
        sql = (sql or "").strip()
        if not sql:
            raise ToolsError(*ERROR_MSG_0073)
        if ';' in sql.rstrip(';'):
            raise ToolsError(*ERROR_MSG_0074)
        if not SqlPermissionGuard.is_query(sql):
            raise ToolsError(*ERROR_MSG_0075)
        SqlPermissionGuard.check(
            sql,
            allow_query=database.test_object.db_c_status == StatusEnum.SUCCESS.value,
            allow_write=False,
        )

        try:
            from sqlalchemy import text
        except ImportError as error:
            raise ToolsError(*ERROR_MSG_0076) from error

        max_rows = max(1, min(int(limit or 100), 100))
        engine = None
        try:
            engine = DataFactoryDatasource.create_engine(database)
            with engine.connect() as connection:
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
                rows = rows[:max_rows]
                return {
                    "columns": list(result.keys()),
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": truncated,
                }
        finally:
            if engine:
                engine.dispose()
