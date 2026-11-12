# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据库视图

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.datasource_alias import DataFactoryDatasourceAliasSerializer, \
    DataFactoryDatasourceAliasSerializerC
from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.data_factory.services.datasource.connection_query import DataSourceConnectionQueryService
from src.apps.data_factory.services.datasource.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.datasource.data_source_execution_request import DataSourceExecutionRequestService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import DATA_SOURCE_ALIAS_NAME_DUPLICATED, RESPONSE_MSG_0210, RESPONSE_MSG_0256


class DataFactoryDatasourceAliasCRUD(ModelCRUD):
    model = DataFactoryDatasourceAlias
    queryset = DataFactoryDatasourceAlias.objects.all()
    serializer_class = DataFactoryDatasourceAliasSerializerC
    serializer = DataFactoryDatasourceAliasSerializer
    page_permission_key = 'config.product'
    not_matching_str = ModelCRUD.not_matching_str + ['source_category', 'db_type']

    def post(self, request: Request):
        """新增逻辑数据源"""
        duplicated = self.get_duplicated_name(request.data)
        if duplicated:
            return ResponseData.fail(
                (DATA_SOURCE_ALIAS_NAME_DUPLICATED[0], DATA_SOURCE_ALIAS_NAME_DUPLICATED[1].format(duplicated.name)))
        return super().post(request)

    def put(self, request: Request):
        """修改逻辑数据源"""
        duplicated = self.get_duplicated_name(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail(
                (DATA_SOURCE_ALIAS_NAME_DUPLICATED[0], DATA_SOURCE_ALIAS_NAME_DUPLICATED[1].format(duplicated.name)))
        return super().put(request)

    @staticmethod
    def get_duplicated_name(data: dict, exclude_id=None):
        """查找同产品下重名的逻辑数据源"""
        project_product = data.get('project_product')
        name = data.get('name')
        if not project_product or not name:
            return None
        queryset = DataFactoryDatasourceAlias.objects.filter(project_product_id=project_product, name=name)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()


class DataFactoryDatasourceAliasViews(ViewSet):

    READ_PERMISSION_KEYS = {
        'config.product:change',
        'api.case:change',
        'ui.case:change',
    }
    WRITE_PERMISSION_KEYS = {
        'api.case:change',
        'ui.case:change',
    }

    @staticmethod
    def _normalize_id_param(value):
        if isinstance(value, dict):
            return value.get('id')
        return value

    @staticmethod
    def _get_param(request: Request, key: str):
        return DataFactoryDatasourceAliasViews._normalize_id_param(request.data.get(key))

    @staticmethod
    def _user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @classmethod
    def _has_any_permission(cls, request: Request, permission_keys: set[str]) -> bool:
        user = cls._user(request)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        user_permissions = PermissionMenuService.permission_keys_for_user(user)
        return bool(user_permissions.intersection(permission_keys))

    @classmethod
    def _has_project_product_scope(cls, request: Request, project_product_id: int) -> bool:
        user = cls._user(request)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        return ProjectProductScopeService.has_project_product(user, project_product_id)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def query(self, request: Request):
        """查询逻辑数据源数据"""
        from src.apps.data_factory.api.serializers.datasource_query import LogicalDatasourceQuerySerializer
        serializer = LogicalDatasourceQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if not self._has_project_product_scope(request, values['project_product_id']):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = DataSourceConnectionQueryService.query_binding(
            values['datasource_alias_id'], values['project_product_id'], values['test_env'], values['sql'],
            operator_id=getattr(self._user(request), 'id', None),
        )
        return ResponseData.success(RESPONSE_MSG_0256, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def execute(self, request: Request):
        """调试数据源操作或检查连接"""
        action = DataSourceExecutionRequestService.normalize_action(request.data.get('action'))
        if action == DataSourceExecutionRequestService.ACTION_TEST_CONNECTION:
            data_source_id = self._get_param(request, 'data_source_id')
            project_product_id = self._get_param(request, 'project_product_id')
            required_permissions = (
                {'config.datasource:change'}
                if data_source_id not in [None, '']
                else {'data_factory.entity:change', 'config.product:change'}
            )
            if not self._has_any_permission(request, required_permissions):
                return ResponseData.fail(RESPONSE_MSG_0210)
            if data_source_id in [None, '']:
                normalized_product_id = DataSourceExecutionService.normalize_id(
                    project_product_id,
                    '项目产品',
                )
                if not self._has_project_product_scope(request, normalized_product_id):
                    return ResponseData.fail(RESPONSE_MSG_0210)
            result = DataSourceExecutionRequestService.test_connection(
                data_source_id,
                datasource_alias_id=self._get_param(request, 'datasource_alias_id'),
                project_product_id=project_product_id,
                test_env=self._get_param(request, 'test_env'),
                target=request.data.get('target'),
            )
            return ResponseData.success(RESPONSE_MSG_0256, result)

        operation = DataSourceExecutionRequestService.inspect_operation(
            datasource_alias_id=self._get_param(request, 'datasource_alias_id'),
            project_product_id=self._get_param(request, 'project_product_id'),
            test_env=self._get_param(request, 'test_env'),
            operation_config=request.data.get('operation_config'),
        )
        permission_keys = (
            self.WRITE_PERMISSION_KEYS if operation['is_write'] else self.READ_PERMISSION_KEYS
        )
        if not self._has_any_permission(request, permission_keys):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if not self._has_project_product_scope(request, operation['project_product_id']):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = DataSourceExecutionRequestService.execute_operation(
            datasource_alias_id=operation['datasource_alias_id'],
            project_product_id=operation['project_product_id'],
            test_env=operation['test_env'],
            operation_config=request.data.get('operation_config'),
            confirm_write=request.data.get('confirm_write', False),
            source_context={**(request.data.get('source_context') or {}),
                            'operator_id': getattr(self._user(request), 'id', None)},
            request_id=request.data.get('request_id'),
        )
        return ResponseData.success(RESPONSE_MSG_0256, result)
