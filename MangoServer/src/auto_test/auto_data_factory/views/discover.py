# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂表结构发现视图

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_data_factory.service.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver
from src.auto_test.auto_data_factory.service.discover import DataFactoryDiscover
from src.auto_test.auto_system.models import Database
from src.tools.decorator.error_response import error_response
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001


class DataFactoryDiscoverViews(ViewSet):
    @staticmethod
    def _get_database(request: Request) -> Database:
        datasource_alias_id = request.data.get('datasource_alias_id') or request.query_params.get('datasource_alias_id')
        test_object_id = request.data.get('test_object_id') or request.query_params.get('test_object_id')
        test_env = request.data.get('test_env') or request.query_params.get('test_env')
        project_product_id = request.data.get('project_product') or request.query_params.get('project_product')
        if datasource_alias_id:
            if test_env and project_product_id:
                return DataFactoryDatasourceResolver.resolve_alias_by_env(
                    datasource_alias_id,
                    project_product_id,
                    test_env,
                )
            return DataFactoryDatasourceResolver.resolve_alias(datasource_alias_id, test_object_id)
        database_id = request.data.get('database_id') or request.query_params.get('database_id')
        return Database.objects.get(id=database_id)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def test_connection(self, request: Request):
        database = self._get_database(request)
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDatasource.test_connection(database))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def tables(self, request: Request):
        database = self._get_database(request)
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDiscover.get_tables(database))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def table(self, request: Request):
        database = self._get_database(request)
        table_name = request.data.get('table_name')
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryDiscover.get_table_schema(database, table_name))
