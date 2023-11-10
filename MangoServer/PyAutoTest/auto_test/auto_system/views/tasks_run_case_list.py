# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TasksRunCaseList
from PyAutoTest.auto_test.auto_system.views.scheduled_tasks import ScheduledTasksSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD


class TasksRunCaseListSerializers(serializers.ModelSerializer):
    class Meta:
        model = TasksRunCaseList
        fields = '__all__'


class TasksRunCaseListSerializersC(serializers.ModelSerializer):
    task = ScheduledTasksSerializers(read_only=True)
    ui_case = UiCaseSerializers(read_only=True)

    class Meta:
        model = TasksRunCaseList
        fields = '__all__'


class TasksRunCaseListCRUD(ModelCRUD):
    model = TasksRunCaseList
    queryset = TasksRunCaseList.objects.all()
    serializer_class = TasksRunCaseListSerializersC
    serializer = TasksRunCaseListSerializers

    def get(self, request: Request):
        books = self.model.objects.filter(task=request.GET.get('id'))
        return ResponseData.success('获取数据成功', [self.serializer_class(i).data for i in books])


class TasksRunCaseListViews(ViewSet):
    model = TasksRunCaseList
    serializer_class = TasksRunCaseListSerializers

    @action(methods=['get'], detail=False)
    def get_type_case_name(self, request: Request):
        _type = request.query_params.get('type')
        if int(_type) == AutoTestTypeEnum.UI.value:
            res = UiCase.objects.values_list('id', 'name')
        else:
            res = ApiCase.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)
