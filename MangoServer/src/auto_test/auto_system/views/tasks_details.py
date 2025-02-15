# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏

from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiCase
from src.auto_test.auto_api.views.api_case import ApiCaseSerializers
from src.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from src.auto_test.auto_system.models import TasksDetails
from src.auto_test.auto_system.views.tasks import TasksSerializers
from src.auto_test.auto_ui.models import UiCase
from src.enums.tools_enum import TestCaseTypeEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class TasksDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'


class TasksDetailsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    task = TasksSerializers(read_only=True)
    ui_case = UiCaseSerializers(read_only=True)
    api_case = ApiCaseSerializers(read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'task',
            'ui_case'
            'api_case'
        )
        return queryset


class TasksDetailsCRUD(ModelCRUD):
    model = TasksDetails
    queryset = TasksDetails.objects.all()
    serializer_class = TasksDetailsSerializersC
    serializer = TasksDetailsSerializers

    @error_response('system')
    def post(self, request: Request):
        _type = int(request.data.get('type'))
        try:
            if _type == TestCaseTypeEnum.UI.value:
                TasksDetails.objects.filter(ui_case_id=request.data.get('ui_case'))
            else:
                TasksDetails.objects.filter(api_case_id=request.data.get('api_case'))

            return ResponseData.fail(RESPONSE_MSG_0112)
        except TasksDetails.DoesNotExist:
            data = self.inside_post(request.data)
            return ResponseData.success(RESPONSE_MSG_0002, data)


class TasksDetailsViews(ViewSet):
    model = TasksDetails
    serializer_class = TasksDetailsSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_type_case_name(self, request: Request):
        _type = int(request.query_params.get('type'))
        module_id = request.query_params.get('module_id')
        if _type == TestCaseTypeEnum.UI.value:
            res = UiCase.objects.filter(module=module_id).values_list('id', 'name')
        else:
            res = ApiCase.objects.filter(module=module_id).values_list('id', 'name')
        return ResponseData.success(RESPONSE_MSG_0065, [{'key': _id, 'title': name} for _id, name in res])

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_set_cases(self, request: Request):
        ### 要修改代码
        case_id_list = request.data.get('case_id_list')
        scheduled_tasks_id = request.data.get('scheduled_tasks_id')
        tasks_run_case_list = self.model.objects.filter(task=scheduled_tasks_id).values_list('case_id')
        tasks_run_case_list = [i[0] for i in list(tasks_run_case_list)]
        for case_id in case_id_list:
            if case_id not in tasks_run_case_list:
                serializer = self.serializer_class(data={'task': scheduled_tasks_id, 'case_id': case_id})
                if serializer.is_valid():
                    serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0066)
        return ResponseData.success(RESPONSE_MSG_0067)
