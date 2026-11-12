# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_public import UiPublicSerializers, UiPublicSerializersC
from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.models import UiPublic, UiCase
from src.apps.auto_ui.api.serializers.configuration_reference import ConfigurationReferenceCountsQuery, ConfigurationReferenceCasesQuery
from src.apps.auto_ui.selectors.configuration_references import UiConfigurationReferenceSelector
from src.common.responses.configuration_references import ConfigurationReferenceViewsMixin
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0021,
    RESPONSE_MSG_0001,
)
from src.apps.auto_ui.selectors.public_variable import UiPublicTagSelector
from src.apps.auto_ui.services.assets.asset_mutation import UiAssetMutationService


class UiPublicCRUD(ModelCRUD):
    def list_response(self, request, books, paging):
        """整理UI 公共变量列表返回数据"""
        if request.query_params.get('tag_summary') == 'true':
            return ResponseData.success(RESPONSE_MSG_0001, UiPublicTagSelector.summarize(books))
        books = UiPublicTagSelector.filter(books, request.query_params.get('tag'),
                                          request.query_params.get('untagged') == 'true')
        return super().list_response(request, books, paging)

    @error_response('ui')
    def put(self, request):
        """修改UI 公共变量"""
        if 'tag_operation' not in request.data:
            return super().put(request)
        scoped = self.filter_queryset_by_data_scope(request, self.queryset.all())
        result = UiAssetMutationService.set_public_tags(scoped, request.data.get('ids'), request.data.get('tags'),
                                                       request.data.get('tag_operation'), self.get_operator_id(request))
        return ResponseData.success(RESPONSE_MSG_0001, result)

    model = UiPublic
    queryset = UiPublic.objects.filter(type__in=UiPublicTypeEnum.get_key_list())
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers
    page_permission_key = 'ui.public'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'datasource_alias',
    ]


class UiPublicViews(ConfigurationReferenceViewsMixin, ViewSet):
    reference_case_model = UiCase
    reference_selector = staticmethod(UiConfigurationReferenceSelector.public_variables)
    reference_counts_query = ConfigurationReferenceCountsQuery
    reference_cases_query = ConfigurationReferenceCasesQuery
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        obj.save(update_fields=["status", "update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0021, )
