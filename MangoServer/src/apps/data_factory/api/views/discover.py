from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.exceptions import (
    DATA_FACTORY_DISCOVER_DATABASE_REQUIRED,
    DATA_FACTORY_DISCOVER_TEST_ENVIRONMENT_REQUIRED,
    DATA_FACTORY_CONFIG_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.services.datasource.datasource_discovery import DataSourceDiscoveryService
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.schema.discover import DataFactoryDiscover
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.services.datasource.data_source import DataSourceConnectionService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现视图


class DataFactoryDiscoverViews(ViewSet):

    TABLES_CACHE_TIMEOUT = 30 * 60

    @staticmethod
    def _get_param(request: Request, key: str):
        data = request.data.get(key)
        if not is_missing_value(data):
            return DataFactoryDiscoverViews._normalize_id_param(data)
        return request.query_params.get(key)

    @staticmethod
    def _normalize_id_param(value):
        if isinstance(value, dict):
            return value.get('id')
        return value

    @staticmethod
    def _get_binding(request: Request):
        datasource_alias_id = DataFactoryDiscoverViews._get_param(request, 'datasource_alias_id')
        test_object_id = DataFactoryDiscoverViews._get_param(request, 'test_object_id')
        test_env = DataFactoryDiscoverViews._get_param(request, 'test_env')
        project_product_id = DataFactoryDiscoverViews._get_param(request, 'project_product')
        if not datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_DISCOVER_DATABASE_REQUIRED)
        if not is_missing_value(test_env) and not is_missing_value(project_product_id):
            return DataFactoryDatasourceResolver.resolve_binding_by_env(
                datasource_alias_id, project_product_id, test_env,
            )
        if not test_object_id:
            raise DataFactoryError(DATA_FACTORY_DISCOVER_TEST_ENVIRONMENT_REQUIRED)
        test_object = DataFactoryDatasourceResolver.get_test_object(test_object_id)
        return DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id, test_object.project_product_id, test_object.environment,
        )

    @staticmethod
    def _is_refresh(request: Request) -> bool:
        value = request.data.get('refresh', request.query_params.get('refresh'))
        return value in [True, 'true', 'True', '1', 1]

    @staticmethod
    def _tables_cache_key(database: Database) -> str:
        version = database.cache_key
        return f'data_factory:discover:tables:{database.id}:{version}'

    @action(methods=['post'], detail=False)
    @error_response('system')
    def tables(self, request: Request):
        """发现数据源中的表"""
        binding = self._get_binding(request)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        if binding.database.db_type in {DataSourceTypeEnum.MYSQL.value,
                                        DataSourceTypeEnum.POSTGRESQL.value} and not binding.database_name:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                                   value=('发现业务表前请在环境绑定中选择数据库；不选库的绑定仅用于限定库名的SQL查询',))
        database = DatasourceTargetService.resolve(binding,
                                                   schema_name=request.data.get('schema_name') or binding.schema_name)
        cache_key = self._tables_cache_key(database)
        if self._is_refresh(request):
            cache.delete(cache_key)
        tables = cache.get(cache_key)
        if tables is None:
            if database.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
                tables = DataSourceDiscoveryService.tables(
                    database, refresh=self._is_refresh(request),
                )['items']
            else:
                tables = DataFactoryDiscover.get_tables(
                    database, timeout_seconds=DataSourceConnectionService.timeout_seconds(),
                )
            cache.set(cache_key, tables, self.TABLES_CACHE_TIMEOUT)
        return ResponseData.success(RESPONSE_MSG_0001, tables)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def table(self, request: Request):
        """获取指定表的结构信息"""
        binding = self._get_binding(request)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        database = DatasourceTargetService.resolve(binding,
                                                   schema_name=request.data.get('schema_name') or binding.schema_name)
        table_name = request.data.get('table_name')
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDiscover.get_table_schema(
            database, table_name, timeout_seconds=DataSourceConnectionService.timeout_seconds(),
        ))
