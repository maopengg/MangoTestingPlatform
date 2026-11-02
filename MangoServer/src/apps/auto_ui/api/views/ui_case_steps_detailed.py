# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-10-17 11:31
# @Author : 毛鹏

from django.core.exceptions import FieldError
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_case_steps_detailed import UiCaseStepsDetailedSerializers, \
    UiCaseStepsDetailedSerializersC
from src.apps.auto_ui.models import UiCaseStepsDetailed
from src.apps.auto_ui.services.case_step_cache import UiCaseStepCacheService
from src.apps.auto_ui.services.step_ordering import UiStepOrderingService
from src.common.decorators.error_response import error_response
from src.common.responses import (
    RESPONSE_MSG_0049,
    RESPONSE_MSG_0050,
    RESPONSE_MSG_0051,
    ResponseData,
)
from src.common.responses.model_crud import ModelCRUD


class UiCaseStepsDetailedCRUD(ModelCRUD):
    model = UiCaseStepsDetailed
    queryset = UiCaseStepsDetailed.objects.all()
    serializer_class = UiCaseStepsDetailedSerializersC
    serializer = UiCaseStepsDetailedSerializers
    page_permission_key = 'ui.case'

    @error_response('ui')
    def get(self, request: Request):
        books = self.model.objects.filter(case=request.GET.get('case_id')).order_by('case_sort')
        try:
            books = self.serializer_class.setup_eager_loading(books)
        except FieldError:
            pass
        return ResponseData.success(RESPONSE_MSG_0049,
                                    self.serializer_class(instance=books,
                                                          many=True).data, )

    def callback(self, _id):
        data = {'id': _id, 'case_flow': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.page_step:
                data['case_flow'] += i.page_step.name
        from src.apps.auto_ui.api.views.ui_case import UiCaseCRUD
        UiCaseCRUD.inside_put(_id, data)


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def post_case_cache_data(self, request: Request):
        result = UiCaseStepCacheService.refresh(
            case_step_id=request.query_params.get('id'),
            case_id=request.query_params.get('case_id'),
            operator_id=UiCaseStepsDetailedCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0050, result)

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        items = request.data.get('case_sort_list') or []
        case_id = request.data.get('case_id')
        if not case_id and items:
            case_id = self.model.objects.values_list(
                'case_id',
                flat=True,
            ).get(id=items[0]['id'])
        UiStepOrderingService.sort_case_steps(
            case_id,
            items,
            UiCaseStepsDetailedCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0051, )
