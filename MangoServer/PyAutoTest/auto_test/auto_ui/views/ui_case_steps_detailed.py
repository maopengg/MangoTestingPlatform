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

from PyAutoTest.auto_test.auto_ui.models import UiCaseStepsDetailed, PageStepsDetailed, UiCase
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import PageStepsSerializers
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view import *
from PyAutoTest.tools.view.model_crud import ModelCRUD


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
        data = {'id': _id, 'case_flow': '', 'name': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.page_step:
                data['case_flow'] += i.page_step.name
        try:
            data['name'] = run[0].case.name
        except AttributeError:
            log.ui.error(f'对UI用例进行排序时报错：{data}')
        from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD
        ui_case = UiCaseCRUD()
        res = ui_case.serializer(instance=UiCase.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            log.ui.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class UiCaseStepsDetailedViews(ViewSet):
    model = UiCaseStepsDetailed
    serializer_class = UiCaseStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def post_case_cache_data(self, request: Request):
        books = self.model.objects.get(id=request.query_params.get('id'))
        ui_page_steps_detailed_obj = PageStepsDetailed.objects.filter(page_step=books.page_step).order_by(
            'step_sort')
        case_data_list = []
        for steps_detailed in ui_page_steps_detailed_obj:
            if steps_detailed.ope_key:
                name = steps_detailed.ele_name.name if steps_detailed.ele_name else steps_detailed.ope_key

                value_dict: dict = steps_detailed.ope_value
                if 'locating' in value_dict:
                    value_dict.pop('locating')
            elif steps_detailed.ope_key:
                name = None
                value_dict: dict = steps_detailed.ope_key
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
                'ope_key': steps_detailed.ope_key,
            })
        books.case_data = case_data_list
        books.save()
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
