# -*- coding: utf-8 -*-
from mangotools.database import (
    DatabaseConnection as SharedDatabaseConnection,
    DatabaseConnectionConfig,
    DatabaseConnectionFactory as SharedDatabaseConnectionFactory,
)
from mangotools.enums import StatusEnum
from mangotools.exceptions import MangoToolsError

from src.apps.data_factory.models import Database
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.exceptions import (
    TEST_CENTER_DATABASE_CONNECTION_DATABASE_TYPE_UNSUPPORTED,
    TestCenterError,
)
from src.apps.test_center.models import TestObject
from src.settings import MYSQL_IP
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum

DatabaseConnection = SharedDatabaseConnection


class DatabaseConnectionAdapter(DatabaseConnection):
    def __init__(self, connection: SharedDatabaseConnection, target):
        super().__init__(
            allow_query=connection.allow_query,
            allow_write=connection.allow_write,
        )
        self.connection = connection
        self.target = target

    def _raise_backend_error(self, error: MangoToolsError):
        if self.target.db_type == DataSourceTypeEnum.MYSQL.value and not self.target.database_name and 'no database selected' in str(
                error).lower():
            from src.apps.data_factory.exceptions import DATA_SOURCE_DEFAULT_DATABASE_REQUIRED, DataFactoryError
            raise DataFactoryError(DATA_SOURCE_DEFAULT_DATABASE_REQUIRED) from error
        raise error

    def condition_execute(self, sql: str):
        try:
            return SqlExecutionAuditService.call(
                self.target, sql, lambda: self.connection.condition_execute(sql),
                source_type=DatasourceAuditSourceEnum.RUNTIME.value, stage=DatasourceAuditStageEnum.CONDITION_EXECUTE.value,
            )
        except MangoToolsError as error:
            self._raise_backend_error(error)

    def execute(self, sql: str):
        try:
            return SqlExecutionAuditService.call(
                self.target, sql, lambda: self.connection.execute(sql),
                source_type=DatasourceAuditSourceEnum.RUNTIME.value, stage=DatasourceAuditStageEnum.EXECUTE.value,
            )
        except MangoToolsError as error:
            self._raise_backend_error(error)

    def close(self) -> None:
        self.connection.close()

    def close_all(self) -> None:
        close_all = getattr(self.connection, "close_all", None)
        if callable(close_all):
            close_all()
        else:
            self.connection.close()


class ObtainDatabase:
    """自定义数据库连接入口"""

    @classmethod
    def build_config(cls, database: Database) -> DatabaseConnectionConfig:
        host = MYSQL_IP if database.host == "db" else database.host
        if database.db_type == DataSourceTypeEnum.SQLITE.value:
            return DatabaseConnectionConfig(database=database.file_path)
        return DatabaseConnectionConfig(
            host=host or "",
            port=database.port or 0,
            user=database.user or "",
            password=database.password,
            database=database.database_name,
        )

    @classmethod
    def create(
            cls,
            database: Database,
            test_object: TestObject | None = None,
            allow_query: bool | None = None,
            allow_write: bool | None = None,
    ) -> DatabaseConnection:
        if allow_query is None:
            allow_query = bool(test_object and test_object.db_c_status == StatusEnum.SUCCESS.value)
        if allow_write is None:
            allow_write = bool(test_object and test_object.db_rud_status == StatusEnum.SUCCESS.value)
        if database.db_type not in {
            DataSourceTypeEnum.MYSQL.value,
            DataSourceTypeEnum.POSTGRESQL.value,
            DataSourceTypeEnum.SQLITE.value,
        }:
            db_type_name = DataSourceTypeEnum.obj().get(database.db_type, database.db_type)
            raise TestCenterError(TEST_CENTER_DATABASE_CONNECTION_DATABASE_TYPE_UNSUPPORTED, value=(db_type_name,))
        return SqlExecutionAuditService.call(
            database, 'CONNECT', lambda: cls._connect(database, allow_query, allow_write),
            stage=DatasourceAuditStageEnum.CONNECT.value, result_summary=lambda _: {'connected': True},
        )

    @classmethod
    def _connect(cls, database, allow_query, allow_write):
        if database.db_type == DataSourceTypeEnum.MYSQL.value:
            from src.apps.test_center.services.managed_sql_connection import ManagedSqlConnection
            return DatabaseConnectionAdapter(ManagedSqlConnection(
                database, allow_query=bool(allow_query), allow_write=bool(allow_write)), database)
        try:
            connection = SharedDatabaseConnectionFactory.create(
                database.db_type,
                cls.build_config(database),
                allow_query=bool(allow_query),
                allow_write=bool(allow_write),
            )
            if database.db_type == DataSourceTypeEnum.POSTGRESQL.value and database.schema_name:
                from psycopg2 import sql
                try:
                    with connection.connection.cursor() as cursor:
                        cursor.execute('SELECT set_config(\'search_path\', %s, false)', (
                            sql.Identifier(database.schema_name).as_string(connection.connection),
                        ))
                except Exception:
                    connection.close()
                    raise
            return DatabaseConnectionAdapter(connection, database)
        except MangoToolsError as error:
            raise


DatabaseConnectionFactory = ObtainDatabase
