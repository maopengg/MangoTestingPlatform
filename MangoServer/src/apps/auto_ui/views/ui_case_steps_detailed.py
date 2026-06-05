# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-10-17 11:31
# @Author : 毛鹏

from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from mangotools.mangos import get_execution_order_with_config_ids
from src.apps.auto_ui.models import UiCaseStepsDetailed, PageStepsDetailed
from src.apps.auto_ui.views.ui_case import UiCaseSerializers
from src.apps.auto_ui.views.ui_page_steps import PageStepsSerializers
from src.common.enums.ui_enum import ElementOperationEnum
from src.common.models.ui_model import StepsDataModel
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view import *
from src.common.tools.view.model_crud import ModelCRUD


class UiCaseStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'


class UiCaseStepsDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = UiCaseSerializers(read_only=True)
    page_step = PageStepsSerializers(read_only=True)

    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'page_step')
        return queryset


class UiCaseStepsDetailedCRUD(ModelCRUD):
    model = UiCaseStepsDetailed
    queryset = UiCaseStepsDetailed.objects.all()
    serializer_class = UiCaseStepsDetailedSerializersC
    serializer = UiCaseStepsDetailedSerializers

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
        from src.apps.auto_ui.views.ui_case import UiCaseCRUD
        UiCaseCRUD.inside_put(_id, data)


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def post_case_cache_data(self, request: Request):
        def m(_id):
            books = self.model.objects.get(id=_id)
            case_data_list = []
            flow_data = books.page_step.flow_data if books.page_step else None
            if not isinstance(flow_data, dict) or not isinstance(flow_data.get('nodes'), list) or not flow_data.get('nodes'):
                return ResponseData.fail(RESPONSE_MSG_0159)
            ids = get_execution_order_with_config_ids(flow_data)
            if ids:
                for page_step_details_id in ids:
                    steps_detailed = PageStepsDetailed.objects.get(id=page_step_details_id)
                    steps_data_model = StepsDataModel(
                        type=steps_detailed.type,
                        ope_key=steps_detailed.ope_key,
                        page_step_details_id=steps_detailed.id,
                        page_step_details_name=steps_detailed.ele_name.name if steps_detailed.ele_name else None,
                        condition_value=steps_detailed.condition_value
                    )
                    if steps_detailed.type == ElementOperationEnum.OPE.value or steps_detailed.type == ElementOperationEnum.ASS.value:
                        page_step_details_data = steps_detailed.ope_value
                    elif steps_detailed.type == ElementOperationEnum.SQL.value:
                        page_step_details_data = steps_detailed.sql_execute
                    elif steps_detailed.type == ElementOperationEnum.CUSTOM.value:
                        page_step_details_data = steps_detailed.custom
                    elif steps_detailed.type == ElementOperationEnum.CONDITION.value:
                        page_step_details_data = steps_detailed.ope_value
                    elif steps_detailed.type == ElementOperationEnum.PYTHON_CODE.value:
                        page_step_details_data = [{'func': steps_detailed.func}]
                    else:
                        return ResponseData.fail(RESPONSE_MSG_0048)

                    steps_data_model.page_step_details_data = page_step_details_data
                    case_data_list.append(steps_data_model.model_dump())
                    # print(steps_data_model.model_dump())
                books.case_data = case_data_list
                books.save()

        _id = request.query_params.get('id', None)
        if _id:
            error_response_data = m(_id)
            if error_response_data:
                return error_response_data
        else:
            case_id = request.query_params.get('case_id', None)
            _books = self.model.objects.filter(case_id=case_id)
            for i in _books:
                error_response_data = m(i.id)
                if error_response_data:
                    return error_response_data
        return ResponseData.success(RESPONSE_MSG_0050)

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        case_id = None
        for i in request.data.get('case_sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.case_sort = i['case_sort']
            case_id = obj.case.id
            obj.save()
        UiCaseStepsDetailedCRUD().callback(case_id)
        return ResponseData.success(RESPONSE_MSG_0051, )
