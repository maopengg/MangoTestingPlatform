# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现视图

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from django.core.cache import cache

from src.apps.auto_data_factory.service.datasource import (
    DataFactoryDatasource,
    DataFactoryDatasourceResolver,
    is_missing_value,
)
from src.apps.auto_data_factory.service.discover import DataFactoryDiscover
from src.apps.auto_system.models import Database
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0001


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
    def _get_database(request: Request) -> Database:
        datasource_alias_id = DataFactoryDiscoverViews._get_param(request, 'datasource_alias_id')
        test_object_id = DataFactoryDiscoverViews._get_param(request, 'test_object_id')
        test_env = DataFactoryDiscoverViews._get_param(request, 'test_env')
        project_product_id = DataFactoryDiscoverViews._get_param(request, 'project_product')
        if datasource_alias_id:
            if not is_missing_value(test_env) and not is_missing_value(project_product_id):
                return DataFactoryDatasourceResolver.resolve_alias_by_env(
                    datasource_alias_id,
                    project_product_id,
                    test_env,
                )
            return DataFactoryDatasourceResolver.resolve_alias(datasource_alias_id, test_object_id)
        database_id = DataFactoryDiscoverViews._get_param(request, 'database_id')
        return Database.objects.get(id=database_id)

    @staticmethod
    def _get_test_object_id(request: Request, database: Database) -> int:
        test_object_id = DataFactoryDiscoverViews._get_param(request, 'test_object_id')
        test_env = DataFactoryDiscoverViews._get_param(request, 'test_env')
        project_product_id = DataFactoryDiscoverViews._get_param(request, 'project_product')
        if not is_missing_value(test_object_id):
            return int(test_object_id)
        if not is_missing_value(test_env) and not is_missing_value(project_product_id):
            return DataFactoryDatasourceResolver.resolve_test_object_id(project_product_id, test_env)
        return database.test_object_id

    @staticmethod
    def _is_refresh(request: Request) -> bool:
        value = request.data.get('refresh', request.query_params.get('refresh'))
        return value in [True, 'true', 'True', '1', 1]

    @staticmethod
    def _tables_cache_key(database: Database) -> str:
        version = database.update_time.strftime('%Y%m%d%H%M%S') if database.update_time else '0'
        return f'data_factory:discover:tables:{database.id}:{version}'

    @action(methods=['post'], detail=False)
    @error_response('system')
    def test_connection(self, request: Request):
        database = self._get_database(request)
        DataFactoryDatasourceResolver.require_permission(self._get_test_object_id(request, database), write=False)
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDatasource.test_connection(database))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def tables(self, request: Request):
        database = self._get_database(request)
        DataFactoryDatasourceResolver.require_permission(self._get_test_object_id(request, database), write=False)
        cache_key = self._tables_cache_key(database)
        if self._is_refresh(request):
            cache.delete(cache_key)
        tables = cache.get(cache_key)
        if tables is None:
            tables = DataFactoryDiscover.get_tables(database)
            cache.set(cache_key, tables, self.TABLES_CACHE_TIMEOUT)
        return ResponseData.success(RESPONSE_MSG_0001, tables)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def table(self, request: Request):
        database = self._get_database(request)
        DataFactoryDatasourceResolver.require_permission(self._get_test_object_id(request, database), write=False)
        table_name = request.data.get('table_name')
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDiscover.get_table_schema(database, table_name))
