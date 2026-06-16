# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据源视图

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.data_factory.service.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.data_factory.service.sql_query import DataFactorySqlQuery
from src.apps.system.views.project_product import ProjectProductSerializersC
from src.common.exceptions import ERROR_MSG_0077, ToolsError
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import RESPONSE_MSG_0189, RESPONSE_MSG_0190


class DataFactoryDatasourceAliasSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryDatasourceAlias
        fields = '__all__'
        validators = []


class DataFactoryDatasourceAliasSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = DataFactoryDatasourceAlias
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'project_product__project')


class DataFactoryDatasourceAliasCRUD(ModelCRUD):
    model = DataFactoryDatasourceAlias
    queryset = DataFactoryDatasourceAlias.objects.all()
    serializer_class = DataFactoryDatasourceAliasSerializerC
    serializer = DataFactoryDatasourceAliasSerializer
    not_matching_str = ModelCRUD.not_matching_str + ['db_type']

    def post(self, request: Request):
        duplicated = self.get_duplicated_code(request.data)
        if duplicated:
            return ResponseData.fail((300, f"当前产品下已存在逻辑数据源编码：{duplicated.code}，请编辑已有数据源或更换编码"))
        return super().post(request)

    def put(self, request: Request):
        duplicated = self.get_duplicated_code(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail((300, f"当前产品下已存在逻辑数据源编码：{duplicated.code}，请编辑已有数据源或更换编码"))
        return super().put(request)

    @staticmethod
    def get_duplicated_code(data: dict, exclude_id=None):
        project_product = data.get('project_product')
        code = data.get('code')
        if not project_product or not code:
            return None
        queryset = DataFactoryDatasourceAlias.objects.filter(project_product_id=project_product, code=code)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()


class DataFactoryDatasourceAliasViews(ViewSet):
    @staticmethod
    def _normalize_id_param(value):
        if isinstance(value, dict):
            return value.get('id')
        return value

    @staticmethod
    def _get_param(request: Request, key: str):
        data = request.data.get(key)
        if not is_missing_value(data):
            return DataFactoryDatasourceAliasViews._normalize_id_param(data)
        return request.query_params.get(key)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def query(self, request: Request):
        datasource_alias_id = self._get_param(request, 'datasource_alias_id') or self._get_param(request, 'id')
        project_product_id = self._get_param(request, 'project_product')
        test_env = self._get_param(request, 'test_env')
        sql = request.data.get('sql') or ''
        try:
            if is_missing_value(test_env):
                raise ToolsError(*ERROR_MSG_0077)
            database = DataFactoryDatasourceResolver.resolve_alias_by_env(
                datasource_alias_id,
                project_product_id,
                test_env,
            )
            data = DataFactorySqlQuery.query(database, sql)
        except Exception as error:
            message = error.msg if isinstance(error, ToolsError) else str(error)
            return ResponseData.fail(RESPONSE_MSG_0190, value=(message,))
        return ResponseData.success(RESPONSE_MSG_0189, data)
