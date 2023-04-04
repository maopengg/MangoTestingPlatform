# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_system.scheduled_tasks.tasks import create_jobs
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class TimeTasksSerializers(serializers.ModelSerializer):
    class Meta:
        model = TimeTasks
        fields = '__all__'


class TimeTasksCRUD(ModelCRUD):
    model = TimeTasks
    queryset = TimeTasks.objects.all()
    serializer_class = TimeTasksSerializers


class TimeTasksViews(ViewSet):

    @staticmethod
    def test(request):
        create_jobs()
        return Response({
            'code': 0
        })
