from rest_framework.request import Request

from src.apps.data_factory.api.serializers.datasource_binding import DataFactoryDatasourceBindingSerializer, \
    DataFactoryDatasourceBindingSerializerC
from src.apps.data_factory.exceptions import DATA_SOURCE_BINDING_CONFLICT, DataFactoryError
from src.apps.data_factory.models import DataFactoryDatasourceBinding
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.common.decorators.error_response import error_response
from src.common.exceptions import SAVE_VALIDATION_FAILED
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0002, RESPONSE_MSG_0116, RESPONSE_MSG_0255


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂逻辑数据库绑定视图


class DataFactoryDatasourceBindingCRUD(ModelCRUD):
    model = DataFactoryDatasourceBinding
    queryset = DataFactoryDatasourceBinding.objects.all()
    serializer_class = DataFactoryDatasourceBindingSerializerC
    serializer = DataFactoryDatasourceBindingSerializer
    page_permission_key = 'config.product'
    not_matching_str = ModelCRUD.not_matching_str + ['datasource_alias', 'database']

    @error_response('system')
    def post(self, request: Request):
        """新增数据源环境绑定"""
        data = self.with_update_user(request, request.data)
        instance = self.get_existing_binding(data)
        if instance:
            return ResponseData.fail(RESPONSE_MSG_0255, value=(self.environment_name(data.get('environment')),))
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0116, serializer.errors)

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        """处理数据源环境绑定新增时的业务逻辑"""
        instance = cls.get_existing_binding(data)
        if instance:
            raise DataFactoryError(DATA_SOURCE_BINDING_CONFLICT, value=(cls.environment_name(data.get('environment')),))
        serializer = cls.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return dict(serializer.data)
        raise DataFactoryError(SAVE_VALIDATION_FAILED, value=(serializer.errors,))

    @staticmethod
    def environment_name(environment) -> str:
        """获取数据源绑定环境名称"""
        try:
            environment = int(environment)
        except (TypeError, ValueError):
            return '当前测试环境'
        return EnvironmentEnum.obj().get(environment, f'环境{environment}')

    @classmethod
    def get_existing_binding(cls, data):
        """查找逻辑数据源已有的环境绑定"""
        datasource_alias = data.get('datasource_alias')
        environment = data.get('environment')
        if not datasource_alias or environment is None:
            return None
        return cls.model.objects.filter(
            datasource_alias_id=datasource_alias,
            environment=environment,
        ).first()
