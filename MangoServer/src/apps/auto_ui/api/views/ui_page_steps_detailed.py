# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from django.core.exceptions import FieldError
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_page_steps_detailed import PageStepsDetailedSerializers, \
    PageStepsDetailedSerializersC, UiDuplicatePageStepNodeSerializer
from src.apps.auto_ui.models import PageStepsDetailed
from src.apps.auto_ui.services.asset_deletion import UiAssetDeletionService
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.apps.auto_ui.services.step_ordering import UiStepOrderingService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0016,
    RESPONSE_MSG_0017,
    RESPONSE_MSG_0018,
    RESPONSE_MSG_0019,
    RESPONSE_MSG_0020,
    RESPONSE_MSG_0035,
    RESPONSE_MSG_0250,
)


class PageStepsDetailedCRUD(ModelCRUD):
    """
        haha
    """
    model = PageStepsDetailed
    queryset = PageStepsDetailed.objects.all()
    serializer_class = PageStepsDetailedSerializersC
    serializer = PageStepsDetailedSerializers
    page_permission_key = 'ui.page_steps'

    @error_response('ui')
    def get(self, request: Request):
        page_step_id = request.GET.get('page_step_id')
        _id = request.GET.get('id')
        if page_step_id:
            books = self.model.objects.filter(page_step_id=page_step_id)
        else:
            books = self.model.objects.filter(id=_id)
        try:
            books = self.serializer_class.setup_eager_loading(books)
        except FieldError:
            pass
        return ResponseData.success(
            RESPONSE_MSG_0016,
            self.serializer_class(instance=books, many=True).data
        )

    @error_response('ui')
    def post(self, request: Request):
        data = PageStepDetailMutationService.save(
            detail_id=request.data.get('id'),
            page_step_id=request.data.get('page_step'),
            node_id=request.data.get('node_id'),
            flow_data=request.data.get('flow_data'),
            payload=request.data,
            page_type=request.data.get('page_type'),
            operator_id=self.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0035, data)

    @error_response('ui')
    def delete(self, request: Request):
        detail_ids = request.query_params.getlist('id[]')
        if request.query_params.get('id'):
            detail_ids.append(request.query_params.get('id'))
        result = UiAssetDeletionService.delete_page_step_details(
            detail_ids=detail_ids,
            page_step_id=request.query_params.get('parent_id'),
        )
        return ResponseData.success(RESPONSE_MSG_0005, result)

    @error_response('ui')
    def callback(self, _id):
        if _id is not None:
            PageStepDetailMutationService.refresh_run_flow(_id)


class PageStepsDetailedView(ViewSet):
    model = PageStepsDetailed
    serializer_class = PageStepsDetailedSerializers

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def duplicate_node(self, request: Request):
        serializer = UiDuplicatePageStepNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = PageStepDetailMutationService.duplicate(
            page_step_id=data['page_step_id'],
            source_detail_id=data['source_detail_id'],
            node_id=data['node_id'],
            flow_data=data['flow_data'],
            operator_id=PageStepsDetailedCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0250, result)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_ope_type(self, request: Request):
        page_type = request.query_params.get('page_type')
        data = PageStepDetailMutationService.method_tree(
            'operation',
            int(page_type) if page_type not in (None, '') else None,
        )
        return ResponseData.success(RESPONSE_MSG_0017, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_ass_type(self, request: Request):
        page_type = request.query_params.get('page_type')
        data = PageStepDetailMutationService.method_tree(
            'assertion',
            int(page_type) if page_type not in (None, '') else None,
        )
        return ResponseData.success(RESPONSE_MSG_0018, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_ass_method(self, request: Request):
        """
        获取断言类型
        @param request:
        @return:
        """
        return ResponseData.success(
            RESPONSE_MSG_0019,
            PageStepDetailMutationService.method_tree('assertion'),
        )

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_step_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        items = request.data.get('step_sort_list') or []
        page_step_id = request.data.get('page_step_id')
        if not page_step_id and items:
            page_step_id = self.model.objects.values_list(
                'page_step_id',
                flat=True,
            ).get(id=items[0]['id'])
        UiStepOrderingService.sort_page_step_details(
            page_step_id,
            items,
            PageStepsDetailedCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0020, )
