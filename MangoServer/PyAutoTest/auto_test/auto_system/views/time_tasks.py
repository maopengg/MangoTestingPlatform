# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import my_task
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class TimeTasksSerializers(serializers.ModelSerializer):
    class Meta:
        model = TimeTasks
        fields = '__all__'


class TimeTasksCRUD(ModelCRUD):
    model = TimeTasks
    queryset = TimeTasks.objects.all()
    serializer_class = TimeTasksSerializers
    serializer = TimeTasksSerializers


class TimeTasksViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_time_data(self, request: Request):
        data = [{'month': []}, {'day': []}, {'hour': []}, {'minute': []}]
        for i in range(1, 13):
            data[0].get('month').append({'key': i, 'title': i})
        for i in range(1, 32):
            data[1].get('day').append({'key': i, 'title': i})
        for i in range(0, 24):
            data[2].get('hour').append({'key': i, 'title': i})
        for i in range(1, 61):
            data[3].get('minute').append({'key': i, 'title': i})
        return Response({
            'code': 200,
            'msg': '获取日期信息成功',
            'data': data
        })

    @action(methods=['get'], detail=False)
    def trigger_timing(self, request: Request):
        case_json, res = my_task(request.query_params.get('id'))
        if res:
            return Response({
                'code': 200,
                'msg': '触发定时任务成功',
                'data': case_json
            })
        else:
            return Response({
                'code': 300,
                'msg': f'触发定时任务失败，请确保{DRIVER}已连接{SERVER}',
                'data': case_json
            })

    @action(methods=['get'], detail=False)
    def get_time_obj_name(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TimeTasks.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': data
        })
