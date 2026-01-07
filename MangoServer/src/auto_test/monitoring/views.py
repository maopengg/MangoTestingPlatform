# -*- coding: utf-8 -*-
# @Description: 预警监控 API（遵循现有 app 风格）
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.monitoring.models import MonitoringTask
from src.auto_test.monitoring.serializers import (
    MonitoringTaskSerializer,
    MonitoringTaskWriteSerializer,
)
from src.auto_test.monitoring.service import runner
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0082


class MonitoringTaskCRUD(ModelCRUD):
    """
    基础增删改查，沿用平台现有 ModelCRUD 规范
    """
    model = MonitoringTask
    queryset = MonitoringTask.objects.all()
    serializer_class = MonitoringTaskSerializer      # 用于 GET 展示
    serializer = MonitoringTaskWriteSerializer       # 用于 POST/PUT 写入


class MonitoringTaskViews(ViewSet):
    """
    任务的启动/停止/日志查询
    """
    model = MonitoringTask
    authentication_classes = []

    @error_response('system')
    def start(self, request: Request):
        task_id = request.data.get('id') or request.query_params.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.error(RESPONSE_MSG_0001, msg='任务不存在')
        runner.start_task(task)
        task.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0002, MonitoringTaskSerializer(task).data)

    @error_response('system')
    def stop(self, request: Request):
        task_id = request.data.get('id') or request.query_params.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.error(RESPONSE_MSG_0001, msg='任务不存在')
        runner.stop_task(task)
        task.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0082, MonitoringTaskSerializer(task).data)

    @error_response('system')
    def logs(self, request: Request):
        task_id = request.query_params.get('id')
        limit = int(request.query_params.get('limit', 200))
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.error(RESPONSE_MSG_0001, msg='任务不存在')
        lines = runner.tail_log(task, limit=limit)
        return ResponseData.success(RESPONSE_MSG_0001, lines)

