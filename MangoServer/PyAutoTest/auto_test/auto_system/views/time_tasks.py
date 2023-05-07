# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TimeTasks
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
    def get_time_data(self, request):
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
