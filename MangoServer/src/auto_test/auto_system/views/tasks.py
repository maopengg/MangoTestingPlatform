# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.models import Tasks
from src.auto_test.auto_system.service.tasks.run_tasks import RunTasks
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.views.test_object import TestObjectSerializersC
from src.auto_test.auto_system.views.time_tasks import TimeTasksSerializers
from src.auto_test.auto_user.views.user import UserSerializers
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class TasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Tasks
        fields = '__all__'


class TasksSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    test_obj = TestObjectSerializersC(read_only=True)
    timing_strategy = TimeTasksSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = Tasks
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'test_obj',
            'timing_strategy',
            'case_people')
        return queryset


class TasksCRUD(ModelCRUD):
    model = Tasks
    queryset = Tasks.objects.all()
    serializer_class = TasksSerializersC
    serializer = TasksSerializers


class TasksViews(ViewSet):
    model = Tasks
    serializer_class = TasksSerializers

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
    def put_notice(self, request: Request):
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
        _tasks_list = self.model.objects.all().values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in _tasks_list]
        return ResponseData.success(RESPONSE_MSG_0099, data)


class TasksNoPermissionViews(ViewSet):
    model = Tasks
    serializer_class = TasksSerializers
    authentication_classes = []

    @action(methods=['get'], detail=False)
    @error_response('system')
    def trigger_timing(self, request: Request):
        RunTasks.trigger(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0100)
