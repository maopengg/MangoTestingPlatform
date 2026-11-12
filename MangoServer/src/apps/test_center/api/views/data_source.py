# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.models import Database
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.datasource.connection_query import DataSourceConnectionQueryService
from src.apps.data_factory.services.datasource.datasource_discovery import DataSourceDiscoveryService
from src.apps.test_center.api.serializers.data_source import DataSourceDiscoverySerializer, DataSourceAliasSerializer
from src.apps.test_center.api.serializers.data_source import DataSourceQuerySerializer
from src.apps.test_center.api.serializers.data_source import DataSourceSerializer, DataSourceSerializerC
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


class DataSourceCRUD(ModelCRUD):
    model = Database
    queryset = Database.objects.all()
    serializer_class = DataSourceSerializerC
    serializer = DataSourceSerializer
    page_permission_key = 'config.datasource'


class DataSourceViews(ViewSet):
    model = Database
    serializer_class = DataSourceDiscoverySerializer

    @error_response('system')
    def query(self, request):
        """查询数据源数据"""
        serializer = DataSourceQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        return ResponseData.success(RESPONSE_MSG_0001, DataSourceConnectionQueryService.query(
            values['data_source_id'], values['database_name'], values['sql'],
            operator_id=getattr(getattr(request.user, 'user_obj', None), 'id', None),
        ))

    @error_response('system')
    def databases(self, request):
        """获取数据源数据库列表"""
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        result = DataSourceDiscoveryService.databases(
            serializer.validated_data['data_source_id'], refresh=serializer.validated_data['refresh'],
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @error_response('system')
    def bindings(self, request):
        """获取数据源环境绑定"""
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        source_id = serializer.validated_data['data_source_id']
        DataSourceDiscoveryService.get_database(source_id)
        user = getattr(request.user, 'user_obj', None)
        items = list(DataFactoryQuerySelector.database_bindings(source_id, user=user))
        return ResponseData.success(RESPONSE_MSG_0001, items)

    @error_response('system')
    def suggest_alias(self, request):
        """推荐数据源逻辑名称"""
        serializer = DataSourceAliasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = DataSourceDiscoveryService.suggest_alias(values['data_source_id'], values['name'])
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @error_response('system')
    def schemas(self, request):
        """获取数据源结构元数据"""
        serializer = DataSourceDiscoverySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        return ResponseData.success(RESPONSE_MSG_0001, DataSourceDiscoveryService.schemas(
            values['data_source_id'], values['database_name'],
        ))
