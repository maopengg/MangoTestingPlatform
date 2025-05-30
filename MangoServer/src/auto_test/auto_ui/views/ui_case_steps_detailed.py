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

from src.auto_test.auto_ui.models import UiCaseStepsDetailed, PageStepsDetailed
from src.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from src.auto_test.auto_ui.views.ui_page_steps import PageStepsSerializers
from src.enums.ui_enum import ElementOperationEnum
from src.models.ui_model import StepsDataModel
from src.tools.decorator.error_response import error_response
from src.tools.view import *
from src.tools.view.model_crud import ModelCRUD


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
        from src.auto_test.auto_ui.views.ui_case import UiCaseCRUD
        UiCaseCRUD.inside_put(_id, data)


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def post_case_cache_data(self, request: Request):
        def m(_id):
            books = self.model.objects.get(id=_id)
            ui_page_steps_detailed_obj = PageStepsDetailed.objects.filter(page_step=books.page_step).order_by(
                'step_sort')
            case_data_list = []
            for steps_detailed in ui_page_steps_detailed_obj:
                steps_data_model = StepsDataModel(
                    type=steps_detailed.type,
                    ope_key=steps_detailed.ope_key,
                    page_step_details_id=steps_detailed.id,
                    page_step_details_data={},

                )
                if steps_detailed.type == ElementOperationEnum.OPE.value:
                    steps_data_model.page_step_details_name = steps_detailed.ele_name.name if steps_detailed.ele_name else steps_detailed.ope_key
                    if steps_detailed.ope_value:
                        steps_data_model.page_step_details_data = {i.get('f'): i.get('v') for i in
                                                                   steps_detailed.ope_value}
                        if 'locating' in steps_data_model.page_step_details_data:
                            steps_data_model.page_step_details_data.pop('locating')
                elif steps_detailed.type == ElementOperationEnum.ASS.value:
                    steps_data_model.page_step_details_name = steps_detailed.ele_name.name if steps_detailed.ele_name else steps_detailed.ope_key
                    if steps_detailed.ope_value:
                        steps_data_model.page_step_details_data = {i.get('f'): i.get('v') for i in
                                                                   steps_detailed.ope_value}
                        if 'actual' in steps_data_model.page_step_details_data:
                            steps_data_model.page_step_details_data.pop('actual')
                elif steps_detailed.type == ElementOperationEnum.SQL.value:
                    steps_data_model.page_step_details_data = {'sql': steps_detailed.sql,
                                                               'key_list': steps_detailed.key_list}
                elif steps_detailed.type == ElementOperationEnum.CUSTOM.value:
                    steps_data_model.page_step_details_data = {'key': steps_detailed.key, 'value': steps_detailed.value}
                else:
                    return ResponseData.fail(RESPONSE_MSG_0048)
                case_data_list.append(steps_data_model.model_dump())
            books.case_data = case_data_list
            books.save()

        _id = request.query_params.get('id', None)
        if _id:
            m(_id)
        else:
            case_id = request.query_params.get('case_id', None)
            _books = self.model.objects.filter(case_id=case_id)
            for i in _books:
                m(i.id)
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
