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

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TasksDetails
from PyAutoTest.auto_test.auto_system.views.tasks import TasksSerializers
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.enums.tools_enum import AutoTestTypeEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


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
    test_object = TestObjectSerializers(read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'task',
            'test_object')
        return queryset


class TasksDetailsCRUD(ModelCRUD):
    model = TasksDetails
    queryset = TasksDetails.objects.all()
    serializer_class = TasksDetailsSerializersC
    serializer = TasksDetailsSerializers

    @error_response('system')
    def get(self, request: Request):
        _type = request.GET.get('type')
        books = self.model.objects.filter(task=request.GET.get('task_id'))
        data = []
        for i in books:
            _dict = model_to_dict(i)
            _dict['task'] = model_to_dict(i.task)
            if int(_type) == AutoTestTypeEnum.UI.value and i.case_id:
                _dict['case_id'] = UiCase.objects.get(id=i.case_id).name
            elif int(_type) == AutoTestTypeEnum.API.value and i.case_id:
                _dict['case_id'] = ApiCase.objects.get(id=i.case_id).name
            data.append(_dict)
        return ResponseData.success(RESPONSE_MSG_0064, data)

    @error_response('system')
    def post(self, request: Request):
        try:
            if request.data.get('case_id'):
                existing_object = self.model.objects.get(task=request.data['task'], case_id=request.data['case_id'])
                if existing_object:
                    return ResponseData.fail(RESPONSE_MSG_0112)
            else:
                data = self.inside_post(request.data)
                return ResponseData.success(RESPONSE_MSG_0002, data)
        except self.model.DoesNotExist:
            data = self.inside_post(request.data)
            return ResponseData.success(RESPONSE_MSG_0002, data)


class TasksDetailsViews(ViewSet):
    model = TasksDetails
    serializer_class = TasksDetailsSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_type_case_name(self, request: Request):
        _type = request.query_params.get('type')
        module_id = request.query_params.get('module_id')
        if int(_type) == AutoTestTypeEnum.UI.value:
            res = UiCase.objects.filter(module=module_id).values_list('id', 'name')
        else:
            res = ApiCase.objects.filter(module=module_id).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0065, data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_set_cases(self, request: Request):
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

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_tasks_case_test_object(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        for i in request.data.get('case_list'):
            serializer = self.serializer_class(
                instance=self.model.objects.get(id=i),
                data={'id': i, 'test_object': request.data.get('test_obj_id')})
            if serializer.is_valid():
                serializer.save()
            else:
                return ResponseData.fail(RESPONSE_MSG_0109, serializer.errors)

        return ResponseData.success(RESPONSE_MSG_0108, )
