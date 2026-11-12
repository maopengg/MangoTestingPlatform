# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂实体视图

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.entity import DataFactoryEntitySerializerC
from src.apps.data_factory.api.serializers.entity_mutation import DataFactoryEntitySerializer
from src.apps.data_factory.enums import DataFactoryEntityStatusChangeSourceEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_DATABASE_ENTITY_UNSUPPORTED,
    DATA_FACTORY_ENTITY_STATUS_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryEntity
from src.apps.data_factory.services.assets.entity import DataFactoryEntityService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import DATA_FACTORY_ENTITY_TABLE_DUPLICATED, RESPONSE_MSG_0001


class DataFactoryEntityCRUD(ModelCRUD):
    model = DataFactoryEntity
    queryset = DataFactoryEntity.objects.all()
    serializer_class = DataFactoryEntitySerializerC
    serializer = DataFactoryEntitySerializer
    page_permission_key = 'data_factory.entity'
    not_matching_str = ModelCRUD.not_matching_str + ['datasource_alias']

    def post(self, request: Request):
        """新增数据工厂实体"""
        duplicated = self.get_duplicated_entity(request.data)
        if duplicated:
            return ResponseData.fail((DATA_FACTORY_ENTITY_TABLE_DUPLICATED[0],
                                      DATA_FACTORY_ENTITY_TABLE_DUPLICATED[1].format(duplicated.table_name)))
        return super().post(request)

    def put(self, request: Request):
        """修改数据工厂实体"""
        duplicated = self.get_duplicated_entity(request.data, request.data.get('id'))
        if duplicated:
            return ResponseData.fail((DATA_FACTORY_ENTITY_TABLE_DUPLICATED[0],
                                      DATA_FACTORY_ENTITY_TABLE_DUPLICATED[1].format(duplicated.table_name)))
        return super().put(request)

    @staticmethod
    def get_duplicated_entity(data: dict, exclude_id=None):
        """查找同归属下重复的数据工厂实体"""
        project_product = data.get('project_product')
        datasource_alias = data.get('datasource_alias')
        table_name = data.get('table_name')
        if not project_product or not datasource_alias or not table_name:
            return None
        queryset = DataFactoryEntity.objects.filter(
            project_product_id=project_product,
            datasource_alias_id=datasource_alias,
            table_name=table_name,
            schema_name=data.get('schema_name', ''),
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()


class DataFactoryEntityViews(ViewSet):

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_generate(self, request: Request):
        """根据表结构批量创建数据工厂实体"""
        result = DataFactoryEntityService.batch_generate(
            project_product_id=request.data.get('project_product'),
            module_id=request.data.get('module'),
            datasource_alias_id=request.data.get('datasource_alias'),
            test_env=request.data.get('test_env'),
            tables=request.data.get('tables') or [],
            sync_fields=request.data.get('sync_fields', True),
            skip_exists=request.data.get('skip_exists', True),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result, len(result["items"]))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def copy(self, request: Request):
        """拒绝不支持的数据工厂实体复制操作"""
        raise DataFactoryError(DATA_FACTORY_ENTITY_DATABASE_ENTITY_UNSUPPORTED)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def status(self, request: Request):
        """设置数据工厂实体启用状态"""
        if request.data.get('status') is None:
            raise DataFactoryError(DATA_FACTORY_ENTITY_STATUS_REQUIRED)
        status = request.data.get('status')
        operator_id = DataFactoryEntityCRUD.get_request_user_id(request)
        action_name = "启用" if status == 1 else "停用"
        result = DataFactoryEntityService.change_status(
            entity_id=request.data.get('id'),
            status=status,
            source=DataFactoryEntityStatusChangeSourceEnum.PAGE_MANUAL.value,
            reason_code=f"manual_{'enabled' if status == 1 else 'disabled'}",
            reason=f"页面手动{action_name}实体",
            operator_id=operator_id,
            restore_invalidated_templates=status == 1,
        )
        entity = result["entity"]
        data = dict(DataFactoryEntitySerializer(entity).data)
        data["template_revalidation"] = {
            "restored_count": result.get("restored_template_count", 0),
            "failed_count": result.get("failed_template_count", 0),
            "failed_templates": result.get("failed_templates", []),
        }
        return ResponseData.success(RESPONSE_MSG_0001, data)
