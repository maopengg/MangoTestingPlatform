from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.case_config import DataFactoryCaseConfigSerializerC
from src.apps.data_factory.api.serializers.mutations import DataFactoryCaseConfigSerializer
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED,
    DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED_CODE_CASE_TYPE_REQUIRED,
    DATA_FACTORY_CASE_CONFIG_STATUS_TEMPLATE_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.case_config import DataFactoryCaseConfigService
from src.apps.data_factory.services.configuration_preview import DataFactoryConfigurationPreviewService
from src.apps.data_factory.services.preview import DataFactoryPreviewService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0013


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂用例配置视图


class DataFactoryCaseConfigCRUD(ModelCRUD):
    model = DataFactoryCaseConfig
    queryset = DataFactoryCaseConfig.objects.all()
    serializer_class = DataFactoryCaseConfigSerializerC
    serializer = DataFactoryCaseConfigSerializer
    page_permission_key = 'data_factory.template'
    not_matching_str = ModelCRUD.not_matching_str + ['template']

    @error_response('system')
    def get(self, request: Request):
        source_type = request.query_params.get('source_type')
        source_id = request.query_params.get('source_id') or request.query_params.get('case')
        if not source_type:
            raise DataFactoryError(DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED)
        queryset = DataFactoryCaseConfig.objects.filter(source_type=source_type)
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        queryset = DataFactoryCaseConfigSerializerC.setup_eager_loading(queryset).order_by('sort', 'id')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DataFactoryCaseConfigSerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class DataFactoryCaseConfigViews(ViewSet):
    action_permission_map = {
        'put_case_sort': 'data_factory.template:edit',
        'preview': 'data_factory.template:detail',
    }

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_case_sort(self, request: Request):
        source_type = request.data.get('source_type')
        if not source_type:
            raise DataFactoryError(DATA_FACTORY_CASE_CONFIG_CASE_TYPE_REQUIRED_CODE_CASE_TYPE_REQUIRED)
        DataFactoryCaseConfigService.sort(
            int(source_type),
            request.data.get('case_sort_list', []),
            update_user_id=request.user.get("id") if isinstance(request.user, dict) else None,
            source="page",
        )
        return ResponseData.success(RESPONSE_MSG_0013)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        template_id = request.data.get('template_id')
        if not template_id:
            raise DataFactoryError(DATA_FACTORY_CASE_CONFIG_STATUS_TEMPLATE_REQUIRED)
        if request.data.get('preview_mode') == 'configuration':
            result = DataFactoryConfigurationPreviewService.preview(
                template_id, request.data.get('field_overrides'), request.data.get('context'),
            )
            return ResponseData.success(RESPONSE_MSG_0001, result)
        result = DataFactoryPreviewService.preview_template(
            template_id=template_id,
            overrides=request.data.get('field_overrides') or {},
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)
