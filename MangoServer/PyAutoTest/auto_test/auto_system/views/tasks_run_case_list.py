# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
import logging

from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TasksRunCaseList
from PyAutoTest.auto_test.auto_system.views.scheduled_tasks import ScheduledTasksSerializers
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('system')


class TasksRunCaseListSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TasksRunCaseList
        fields = '__all__'


class TasksRunCaseListSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    task = ScheduledTasksSerializers(read_only=True)
    test_object = TestObjectSerializers(read_only=True)

    class Meta:
        model = TasksRunCaseList
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'task',
            'test_object')
        return queryset


class TasksRunCaseListCRUD(ModelCRUD):
    model = TasksRunCaseList
    queryset = TasksRunCaseList.objects.all()
    serializer_class = TasksRunCaseListSerializersC
    serializer = TasksRunCaseListSerializers

    def get(self, request: Request):
        _type = request.GET.get('type')
        books = self.model.objects.filter(task=request.GET.get('id')).order_by('sort')
        data = []
        for i in books:
            _dict = model_to_dict(i)
            _dict['task'] = model_to_dict(i.task)
            if i.test_object:
                _dict['test_object'] = model_to_dict(i.test_object)
            if int(_type) == AutoTestTypeEnum.UI.value and i.case:
                _dict['case'] = UiCase.objects.get(id=i.case).name
            elif int(_type) == AutoTestTypeEnum.API.value and i.case:
                _dict['case'] = ApiCase.objects.get(id=i.case).name
            data.append(_dict)
        return ResponseData.success(RESPONSE_MSG_0064, data)

    def post(self, request: Request):
        serializer = self.serializer(data=request.data)
        try:
            existing_object = self.model.objects.get(task=request.data['task'], case=request.data['case'])
            if existing_object:
                return ResponseData.fail(RESPONSE_MSG_0112)
        except self.model.DoesNotExist:
            if serializer.is_valid():
                serializer.save()
                self.asynchronous_callback(request)
                return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
            else:
                log.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
                return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)


class TasksRunCaseListViews(ViewSet):
    model = TasksRunCaseList
    serializer_class = TasksRunCaseListSerializers

    @action(methods=['get'], detail=False)
    def get_type_case_name(self, request: Request):
        _type = request.query_params.get('type')
        module_name = request.query_params.get('module_name')
        if int(_type) == AutoTestTypeEnum.UI.value:
            res = UiCase.objects.filter(module_name=module_name).values_list('id', 'name')
        else:
            res = ApiCase.objects.filter(module_name=module_name).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0065, data)

    @action(methods=['post'], detail=False)
    def batch_set_cases(self, request: Request):
        case_id_list = eval(request.data.get('case_id_list'))
        scheduled_tasks_id = request.data.get('scheduled_tasks_id')
        tasks_run_case_list = self.model.objects.filter(task=scheduled_tasks_id).values_list('case')
        tasks_run_case_list = [i[0] for i in list(tasks_run_case_list)]
        for case_id in case_id_list:
            if case_id not in tasks_run_case_list:
                serializer = self.serializer_class(data={'task': scheduled_tasks_id, 'case': case_id})
                if serializer.is_valid():
                    serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0066)
        return ResponseData.success(RESPONSE_MSG_0067)

    @action(methods=['put'], detail=False)
    def put_tasks_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        for i in request.data.get('sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.sort = i['sort']
            obj.save()
        return ResponseData.success(RESPONSE_MSG_0107, )

    @action(methods=['put'], detail=False)
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
