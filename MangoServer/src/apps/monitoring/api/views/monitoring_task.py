# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2026-01-06
# @Author :
import os

from django.conf import settings
from django.http import FileResponse
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.monitoring.api.serializers.monitoring_task import (
    MonitoringTaskSerializers,
    MonitoringTaskSerializersC,
)
from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.models import MonitoringTask
from src.apps.monitoring.services.runner import MonitoringTaskRunner
from src.apps.monitoring.services.task_control import MonitoringTaskControlService
from src.apps.monitoring.services.task_log import MonitoringTaskLogService
from src.apps.monitoring.selectors.task import MonitoringTaskSelector
from src.common.decorators.error_response import error_response
from src.common.decorators.system_error import report_system_error
from src.common.enums.system_error import SystemErrorEventSource
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    MONITORING_REPORT_DOWNLOAD_FAILED,
    RESPONSE_MSG_0142, RESPONSE_MSG_0145, RESPONSE_MSG_0146, RESPONSE_MSG_0148, RESPONSE_MSG_0149, RESPONSE_MSG_0150
)


def _ensure_dirs():
    scripts_dir = settings.MONITORING_SCRIPT_DIR
    logs_dir = settings.MONITORING_LOG_DIR
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    return scripts_dir, logs_dir


class MonitoringTaskCRUD(ModelCRUD):
    model = MonitoringTask
    queryset = MonitoringTask.objects.all()
    serializer_class = MonitoringTaskSerializersC
    serializer = MonitoringTaskSerializers
    page_permission_key = 'monitoring.task'


class MonitoringTaskViews(ViewSet):
    """
    监控任务视图
    """
    model = MonitoringTask
    serializer_class = MonitoringTaskSerializers

    @error_response('system')
    def start(self, request: Request):
        task_id = request.data.get('id') or request.query_params.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0142)
        task = MonitoringTaskControlService.request_start(task)
        return ResponseData.success(RESPONSE_MSG_0148, MonitoringTaskSerializers(task).data)

    @error_response('system')
    def stop(self, request: Request):
        task_id = request.data.get('id') or request.query_params.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0142)
        task.status = MonitoringTaskStatusEnum.STOPPED.value
        task.save(update_fields=['status', 'update_time'])
        task.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0149, MonitoringTaskSerializers(task).data)

    @error_response('system')
    def logs(self, request: Request):
        task_id = request.query_params.get('id')
        limit = int(request.query_params.get('limit', 200))
        task = MonitoringTaskSelector.get(request.user.user_obj, task_id)
        result = MonitoringTaskLogService.read_task(task, limit=limit)
        lines = [line + '\n' for line in result['lines']]
        return ResponseData.success(RESPONSE_MSG_0150, lines)

    @error_response('system')
    def download_log(self, request: Request):
        """
        下载日志文件
        """
        task_id = request.query_params.get('id') or request.data.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0142)

        if not task.log_path:
            return ResponseData.fail(RESPONSE_MSG_0145)

        # 将相对路径转换为绝对路径，兼容新 runtime 路径和历史日志路径。
        log_path = MonitoringTaskRunner._get_absolute_path(task.log_path)

        if not os.path.exists(log_path):
            return ResponseData.fail(RESPONSE_MSG_0146)

        try:
            file = open(log_path, 'rb')
            filename = f'任务日志_{task.name}_{task.id}.log'
            response = FileResponse(file, as_attachment=True, filename=filename)
            return response
        except Exception as e:
            report_system_error(e, source=SystemErrorEventSource.HTTP, request=request)
            return ResponseData.fail(MONITORING_REPORT_DOWNLOAD_FAILED)
