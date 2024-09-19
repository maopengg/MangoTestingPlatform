# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import ScheduledTasks
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import Tasks
from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksSerializers
from PyAutoTest.auto_test.auto_user.views.test_object import TestObjectSerializersC
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class ScheduledTasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ScheduledTasks
        fields = '__all__'


class ScheduledTasksSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    test_obj = TestObjectSerializersC(read_only=True)
    timing_strategy = TimeTasksSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = ScheduledTasks
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'test_obj',
            'timing_strategy',
            'case_people')
        return queryset


class ScheduledTasksCRUD(ModelCRUD):
    model = ScheduledTasks
    queryset = ScheduledTasks.objects.all()
    serializer_class = ScheduledTasksSerializersC
    serializer = ScheduledTasksSerializers


class ScheduledTasksViews(ViewSet):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializers

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0097, )

    @action(methods=['put'], detail=False)
    @error_response('system')
    def put_is_notice(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.is_notice = request.data.get('is_notice')
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0098, )

    @action(methods=['put'], detail=False)
    @error_response('system')
    def get_id_name(self, request: Request):
        """
        获取定时任务列表
        :param request:
        :return:
        """
        case_type = request.query_params.get('case_type')
        scheduled_tasks_list = self.model.objects.filter(type=case_type).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in scheduled_tasks_list]
        return ResponseData.success(RESPONSE_MSG_0099, data)


class ScheduledTasksNoPermissionViews(ViewSet):
    model = ScheduledTasks
    serializer_class = ScheduledTasksSerializers
    authentication_classes = []

    @action(methods=['get'], detail=False)
    @error_response('system')
    def trigger_timing(self, request: Request):
        Tasks.trigger(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0100)

