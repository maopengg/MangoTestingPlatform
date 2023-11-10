# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import ScheduledTasks
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import my_task
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class ScheduledTasksSerializers(serializers.ModelSerializer):
    class Meta:
        model = ScheduledTasks
        fields = '__all__'


class ScheduledTasksSerializersC(serializers.ModelSerializer):
    test_obj = TestObjectSerializers(read_only=True)
    timing_strategy = TimeTasksSerializers(read_only=True)
    executor_name = UserSerializers(read_only=True)

    class Meta:
        model = ScheduledTasks
        fields = '__all__'


class ScheduledTasksCRUD(ModelCRUD):
    model = ScheduledTasks
    queryset = ScheduledTasks.objects.all()
    serializer_class = ScheduledTasksSerializersC
    serializer = ScheduledTasksSerializers


class ScheduledTasksQuery(ModelQuery):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializersC


class ScheduledTasksViews(ViewSet):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializers

    @action(methods=['get'], detail=False)
    def get_test(self, request: Request):
        my_task(1)
        return ResponseData.success('获取数据成功', )

    @action(methods=['put'], detail=False)
    def put_state(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success('修改定时任务状态成功', )
