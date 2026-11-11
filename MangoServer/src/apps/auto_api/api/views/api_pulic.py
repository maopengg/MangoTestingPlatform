# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_pulic import ApiPublicSerializers, ApiPublicSerializersC
from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.models import ApiPublic, ApiCase
from src.apps.auto_api.api.serializers.configuration_reference import ConfigurationReferenceCountsQuery, ConfigurationReferenceCasesQuery
from src.apps.auto_api.selectors.configuration_references import ApiConfigurationReferenceSelector
from src.common.responses.configuration_references import ConfigurationReferenceViewsMixin
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0104,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, save_update_user
from src.apps.auto_api.selectors.public_variable import ApiPublicTagSelector
from src.apps.auto_api.services.api_public import ApiPublicMutationService
from src.common.responses.response_msg import RESPONSE_MSG_0001


class ApiPublicCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    def list_response(self, request, books, paging):
        if request.query_params.get('tag_summary') == 'true':
            return ResponseData.success(RESPONSE_MSG_0001, ApiPublicTagSelector.summarize(books))
        books = ApiPublicTagSelector.filter(books, request.query_params.get('tag'),
                                           request.query_params.get('untagged') == 'true')
        return super().list_response(request, books, paging)

    @error_response('api')
    def put(self, request):
        if 'tag_operation' not in request.data:
            return super().put(request)
        scoped = self.filter_queryset_by_data_scope(request, self.queryset.all())
        result = ApiPublicMutationService.set_tags(scoped, request.data.get('ids'), request.data.get('tags'),
                                                 request.data.get('tag_operation'), self.get_operator_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, result)

    model = ApiPublic
    queryset = ApiPublic.objects.filter(type__in=ApiPublicTypeEnum.get_key_list())
    serializer_class = ApiPublicSerializersC
    serializer = ApiPublicSerializers
    page_permission_key = 'api.public'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'datasource_alias',
        'update_user',
    ]


class ApiPublicViews(ConfigurationReferenceViewsMixin, ViewSet):
    reference_case_model = ApiCase
    reference_selector = staticmethod(ApiConfigurationReferenceSelector.public_variables)
    reference_counts_query = ConfigurationReferenceCountsQuery
    reference_cases_query = ConfigurationReferenceCasesQuery
    model = ApiPublic
    serializer_class = ApiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """

        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        save_update_user(obj, request, ['status'])
        return ResponseData.success(RESPONSE_MSG_0104, )
