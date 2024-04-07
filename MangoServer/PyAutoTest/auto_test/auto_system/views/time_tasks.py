# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import RESPONSE_MSG_0103


class TimeTasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

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
    def get_time_obj_name(self, request):
        """
         获取平台枚举
         :param request:
         :return:
         """
        res = TimeTasks.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0103, data)
