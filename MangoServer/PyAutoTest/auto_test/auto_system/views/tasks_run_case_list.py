# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TasksRunCaseList
from PyAutoTest.auto_test.auto_system.views.scheduled_tasks import ScheduledTasksSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


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

    class Meta:
        model = TasksRunCaseList
        fields = '__all__'


class TasksRunCaseListCRUD(ModelCRUD):
    model = TasksRunCaseList
    queryset = TasksRunCaseList.objects.all()
    serializer_class = TasksRunCaseListSerializersC
    serializer = TasksRunCaseListSerializers

    def get(self, request: Request):
        _type = request.GET.get('type')
        books = self.model.objects.filter(task=request.GET.get('id'))
        data = []
        for i in books:
            _dict = model_to_dict(i)
            _dict['task'] = model_to_dict(i.task)
            if int(_type) == AutoTestTypeEnum.UI.value and i.case:
                _dict['case'] = UiCase.objects.get(id=i.case).name
            elif int(_type) == AutoTestTypeEnum.API.value and i.case:
                _dict['case'] = ApiCase.objects.get(id=i.case).name
            data.append(_dict)
        return ResponseData.success('获取数据成功', data)


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
        return ResponseData.success('获取数据成功', data)

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
                    return ResponseData.fail('批量设置到定时任务失败')
        return ResponseData.success('批量设置到定时任务成功')
