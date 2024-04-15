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

from PyAutoTest.auto_test.auto_ui.models import UiCaseStepsDetailed, UiPageStepsDetailed, UiCase
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsSerializers
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData
from PyAutoTest.tools.view_utils.response_msg import *

logger = logging.getLogger('system')


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
        return ResponseData.success(RESPONSE_MSG_0049, data)

    def callback(self, _id):
        """
        排序
        @param _id: 用例ID
        @return:
        """
        data = {'id': _id, 'case_flow': '', 'name': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.page_step:
                data['case_flow'] += i.page_step.name
        try:
            data['name'] = run[0].case.name
        except AttributeError:
            logger.error(f'对UI用例进行排序时报错：{data}')
        from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD
        ui_case = UiCaseCRUD()
        res = ui_case.serializer(instance=UiCase.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            logger.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    def post_case_cache_data(self, request: Request):
        books = self.model.objects.get(id=request.query_params.get('id'))
        ui_page_steps_detailed_obj = UiPageStepsDetailed.objects.filter(page_step=books.page_step).order_by(
            'step_sort')
        case_data_list = []
        for steps_detailed in ui_page_steps_detailed_obj:
            if steps_detailed.ope_type:
                name = steps_detailed.ele_name.name if steps_detailed.ele_name else steps_detailed.ope_type

                value_dict: dict = steps_detailed.ope_value
                if 'locating' in value_dict:
                    value_dict.pop('locating')
            elif steps_detailed.ass_type:
                name = None
                value_dict: dict = steps_detailed.ass_value
                if 'value' in value_dict:
                    value_dict.pop('value')
            elif steps_detailed.sql:
                name = None
                value_dict = {'sql': steps_detailed.sql, 'key_list': steps_detailed.key_list}
            elif steps_detailed.key and steps_detailed.value:
                name = None
                value_dict = {'key': steps_detailed.key, 'value': steps_detailed.value}
            else:
                return ResponseData.fail(RESPONSE_MSG_0048)
            case_data_list.append({
                'page_step_details_id': steps_detailed.id,
                'page_step_details_name': name,
                'page_step_details_data': value_dict,
                'type': steps_detailed.type,
                'ope_type': steps_detailed.ope_type,
                'ass_type': steps_detailed.ass_type,
            })
        books.case_data = case_data_list
        books.save()
        return ResponseData.success(RESPONSE_MSG_0050)

    @action(methods=['put'], detail=False)
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
