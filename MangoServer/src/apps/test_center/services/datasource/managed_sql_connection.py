from mangotools.database import DatabaseConnection, SqlPermissionGuard

from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.system.services.configuration.system_config import SystemConfigService


class ManagedSqlConnection(DatabaseConnection):
    """旧 Case 接口的适配器；不再使用内部包中可能自动重放写入的连接池。"""
    def __init__(self, target, *, allow_query, allow_write):
        super().__init__(allow_query=allow_query, allow_write=allow_write)
        self.target = target
        self.engine = DataFactoryDatasource.create_engine(target)
        try:
            with self.engine.connect():
                pass
        except BaseException:
            self.engine.dispose()
            raise

    def execute(self, sql):
        SqlPermissionGuard.check(sql, self.allow_query, self.allow_write)
        DatasourceCostService.sql(sql)
        if self.engine._mango_pool_size != DatasourceGovernorService.policy().pool_size:
            self.engine.dispose()
            self.engine = DataFactoryDatasource.create_engine(self.target)
        query = SqlPermissionGuard.is_query(sql)
        try:
            with DatasourceGovernorService.operation(self.target):
                with (self.engine.connect() if query else self.engine.begin()) as connection:
                    result = connection.execution_options(stream_results=query).exec_driver_sql(sql)
                    if result.returns_rows:
                        maximum = SystemConfigService.get_ranged_int('DATA_QUERY_MAX_ROWS')
                        rows = result.mappings().fetchmany(maximum + 1)
                        if len(rows) > maximum:
                            DatasourceCostService.abort_result(connection, result)
                        return self.convert_datetime_to_string([dict(row) for row in rows])
                    return result.rowcount
        except DataFactoryError:
            raise
        except Exception as error:
            DataSourceErrorService.raise_sql_error(self.target, error)

    def close(self):
        pass

    def close_all(self):
        self.engine.dispose()
