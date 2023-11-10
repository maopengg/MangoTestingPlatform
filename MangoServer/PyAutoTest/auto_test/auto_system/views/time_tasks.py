# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import my_task
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class TimeTasksSerializers(serializers.ModelSerializer):
    class Meta:
        model = TimeTasks
        fields = '__all__'


class TimeTasksCRUD(ModelCRUD):
    model = TimeTasks
    queryset = TimeTasks.objects.all()
    serializer_class = TimeTasksSerializers
    serializer = TimeTasksSerializers


class TimeTasksQuery(ModelQuery):
    """
    条件查
    """
    model = TimeTasks
    serializer_class = TimeTasksSerializers


class TimeTasksViews(ViewSet):

    @action(methods=['get'], detail=False)
    def trigger_timing(self, request: Request):
        case_json, res = my_task(request.query_params.get('id'))
        if res:
            return ResponseData.success('触发定时任务成功', case_json)

        else:
            return ResponseData.fail(f'触发定时任务失败，请确保{DRIVER}已连接{SERVER}', case_json)

    @action(methods=['get'], detail=False)
    def get_time_obj_name(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TimeTasks.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)
