from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.field import DataFactoryFieldSerializerC
from src.apps.data_factory.api.serializers.mutations import DataFactoryFieldSerializer
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_FIELD_REQUIRED,
    DATA_FACTORY_FIELD_INVALID_CODE_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryEntity, DataFactoryField
from src.apps.data_factory.services.field import DataFactoryFieldService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂字段规则视图


class DataFactoryFieldCRUD(ModelCRUD):
    model = DataFactoryField
    queryset = DataFactoryField.objects.all()
    serializer_class = DataFactoryFieldSerializerC
    serializer = DataFactoryFieldSerializer
    page_permission_key = 'data_factory.entity'
    not_matching_str = ModelCRUD.not_matching_str + ['entity']

    @error_response('system')
    def get(self, request: Request):
        queryset = DataFactoryFieldSerializerC.setup_eager_loading(DataFactoryField.objects.all())
        entity_id = request.query_params.get('entity')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__contains=name)

        queryset = queryset.order_by('sort', 'id')
        page_size = request.query_params.get("pageSize")
        page = request.query_params.get("page")
        if page_size and page:
            data_list, count = self.paging_list(
                page_size,
                page,
                queryset,
                DataFactoryFieldSerializerC,
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DataFactoryFieldSerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class DataFactoryFieldViews(ViewSet):
    action_permission_map = {
        'batch_save': 'data_factory.entity:edit',
        'preview_values': 'data_factory.entity:debug',
    }

    @staticmethod
    def save_schema_fields(entity: DataFactoryEntity, columns: list, replace: bool = True, update_user_id=None) -> list:
        return DataFactoryFieldService.save_schema_fields(entity, columns, replace, update_user_id)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_save(self, request: Request):
        entity_id = request.data.get('entity_id')
        fields = request.data.get('fields') or []
        replace = request.data.get('replace', False)
        if not entity_id:
            raise DataFactoryError(DATA_FACTORY_FIELD_REQUIRED)
        if not isinstance(fields, list):
            raise DataFactoryError(DATA_FACTORY_FIELD_INVALID_CODE_INVALID)

        entity = DataFactoryEntity.objects.get(id=entity_id)
        update_user_id = request.user.get("id") if isinstance(getattr(request, "user", None), dict) else None
        saved_fields = DataFactoryFieldService.save_schema_fields(entity, fields, replace, update_user_id)

        return ResponseData.success(RESPONSE_MSG_0001, saved_fields, len(saved_fields))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview_values(self, request: Request):
        result = DataFactoryFieldService.preview_values(
            fields=request.data.get('fields') or [],
            context=request.data.get('context') or {},
            entity_id=request.data.get('entity_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result, len(result["fields"]))

    @staticmethod
    def normalize_field_data(field_data: dict):
        return DataFactoryFieldService.normalize_field_data(field_data)

    @staticmethod
    def normalize_dependency_config(generator_config: dict) -> dict:
        return DataFactoryFieldService.normalize_dependency_config(generator_config)

    @staticmethod
    def preview_dependency_field(field: DataFactoryField, context: dict):
        return DataFactoryFieldService.preview_dependency_field(field, context)
