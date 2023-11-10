# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-10-17 11:31
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiCaseStepsDetailed, UiPageStepsDetailed
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('system')


class UiCaseStepsDetailedSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'


class UiCaseStepsDetailedSerializersC(serializers.ModelSerializer):
    case = UiCaseSerializers(read_only=True)
    page_step = UiPageStepsSerializers(read_only=True)

    class Meta:
        model = UiCaseStepsDetailed
        fields = '__all__'


class UiCaseStepsDetailedCRUD(ModelCRUD):
    model = UiCaseStepsDetailed
    queryset = UiCaseStepsDetailed.objects.all()
    serializer_class = UiCaseStepsDetailedSerializersC
    serializer = UiCaseStepsDetailedSerializers

    def get(self, request: Request):
        books = self.model.objects.filter(case=request.GET.get('case_id')).order_by('case_sort')
        data = [self.serializer_class(i).data for i in books]

        for i in data:
            i['case_cache_data'] = eval(i.get('case_cache_data'))
        return ResponseData.success('获取数据成功', data)


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['post'], detail=False)
    def post_case_cache_data(self, request: Request):
        books = self.model.objects.get(id=request.query_params.get('id'))
        ui_page_steps_detailed_list = UiPageStepsDetailed.objects.filter(
            page_step=books.page_step).order_by('step_sort')
        data_list = []
        for e in ui_page_steps_detailed_list:
            if e.ope_value:
                value_dict: dict = eval(e.ope_value)
                value_dict.pop('locating')
                if value_dict:
                    data_list.append({e.ele_name_a.name: value_dict})
        books.case_cache_data = data_list
        ass_list = []
        for e in ui_page_steps_detailed_list:
            if e.ass_value:
                value_dict: dict = eval(e.ass_value)
                value_dict.pop('value')
                if value_dict:
                    ass_list.append({e.ele_name_a.name: value_dict})
        books.case_cache_ass = ass_list

        books.save()
        return ResponseData.success('刷新成功')
