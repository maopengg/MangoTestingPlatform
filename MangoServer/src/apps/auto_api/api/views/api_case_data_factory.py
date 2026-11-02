from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_case_data_factory import ApiCaseDataFactorySerializer, \
    ApiCaseDataFactorySerializerC
from src.apps.auto_api.exceptions import (
    AUTO_API_API_CASE_DATA_FACTORY_STATUS_TEMPLATE_REQUIRED,
    AutoApiError,
)
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.case_config import DataFactoryCaseConfigService
from src.apps.data_factory.services.preview import DataFactoryPreviewService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0013


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例数据工厂配置视图


class ApiCaseDataFactoryCRUD(ModelCRUD):
    model = DataFactoryCaseConfig
    queryset = DataFactoryCaseConfig.objects.all()
    serializer_class = ApiCaseDataFactorySerializerC
    serializer = ApiCaseDataFactorySerializer
    page_permission_key = 'api.case'
    not_matching_str = ModelCRUD.not_matching_str + ['case', 'template', 'source_type', 'source_id']

    @error_response('api')
    def get(self, request: Request):
        case_id = request.query_params.get('case') or request.query_params.get('source_id')
        queryset = DataFactoryCaseConfig.objects.filter(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
        )
        if case_id:
            queryset = queryset.filter(source_id=case_id)
        queryset = ApiCaseDataFactorySerializerC.setup_eager_loading(queryset).order_by('sort', 'id')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseDataFactorySerializerC(instance=queryset, many=True).data,
            queryset.count(),
        )


class ApiCaseDataFactoryViews(ViewSet):

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_case_sort(self, request: Request):
        DataFactoryCaseConfigService.sort(
            DataFactoryCaseSourceTypeEnum.API_CASE.value,
            request.data.get('case_sort_list', []),
            update_user_id=ApiCaseDataFactoryCRUD.get_request_user_id(request),
            source="page",
        )
        return ResponseData.success(RESPONSE_MSG_0013)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def preview(self, request: Request):
        template_id = request.data.get('template_id')
        if not template_id:
            raise AutoApiError(AUTO_API_API_CASE_DATA_FACTORY_STATUS_TEMPLATE_REQUIRED)
        result = DataFactoryPreviewService.preview_template(
            template_id=template_id,
            overrides=request.data.get('field_overrides') or {},
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)
