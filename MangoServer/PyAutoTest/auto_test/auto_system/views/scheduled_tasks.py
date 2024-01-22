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
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import Tasks
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


class ScheduledTasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ScheduledTasks
        fields = '__all__'


class ScheduledTasksSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
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


class ScheduledTasksViews(ViewSet):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializers

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success('修改定时任务状态成功', )

    @action(methods=['put'], detail=False)
    def put_is_notice(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.is_notice = request.data.get('is_notice')
        obj.save()
        return ResponseData.success('修改通知状态成功', )


class ScheduledTasksNoPermissionViews(ViewSet):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializers
    authentication_classes = []

    @action(methods=['get'], detail=False)
    def trigger_timing(self, request: Request):
        try:
            data = Tasks.trigger(request.query_params.get('id'))
            return ResponseData.success('触发定时任务成功，任务正在进行中...', data)
        except MangoServerError as error:
            return ResponseData.fail(error.msg, )
