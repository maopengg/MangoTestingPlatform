# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 预警监控报告视图
# @Time   : 2026-01-08
# @Author :
from mangotools.enums import StatusEnum
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.monitoring.api.serializers.monitoring_report import MonitoringReportSerializers, \
    MonitoringReportSerializersC
from src.apps.monitoring.enums import MonitoringLogStatusEnum
from src.apps.monitoring.models import MonitoringReport, MonitoringTask
from src.common.decorators.error_response import error_response
from src.common.decorators.system_error import report_system_error
from src.common.enums.system_error import SystemErrorEventSource
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    MONITORING_REPORT_CREATE_FAILED,
    RESPONSE_MSG_0151, RESPONSE_MSG_0152, RESPONSE_MSG_0153
)


class MonitoringReportCRUD(ModelCRUD):
    model = MonitoringReport
    queryset = MonitoringReport.objects.all()
    serializer_class = MonitoringReportSerializersC
    serializer = MonitoringReportSerializers
    page_permission_key = 'monitoring.report'


class MonitoringReportViews(ViewSet):
    """
    监控报告视图
    """
    model = MonitoringReport
    serializer_class = MonitoringReportSerializers

    @error_response('system')
    def create_report(self, request: Request):
        """
        创建监控报告
        """
        task_id = request.data.get('task_id')
        status = request.data.get('status')
        msg = request.data.get('msg', '')
        detail = request.data.get('detail', None)

        # 验证必填字段
        if not task_id:
            return ResponseData.fail(RESPONSE_MSG_0151, 'task_id 不能为空')
        if status is None:
            return ResponseData.fail(RESPONSE_MSG_0151, 'status 不能为空')
        if not msg:
            return ResponseData.fail(RESPONSE_MSG_0151, 'msg 不能为空')

        # 验证任务是否存在
        try:
            task = MonitoringTask.objects.get(id=task_id)
        except MonitoringTask.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0152, '关联的任务不存在')

        # 验证状态值
        valid_statuses = [
            MonitoringLogStatusEnum.INFO.value,  # 0: 信息
            MonitoringLogStatusEnum.ERROR.value,  # 1: 失败
            MonitoringLogStatusEnum.WARNING.value,  # 2: 警告
            MonitoringLogStatusEnum.DEBUG.value,  # 3: 调试
        ]
        if status not in valid_statuses:
            return ResponseData.fail(RESPONSE_MSG_0151, f'status 必须是 {valid_statuses} 之一')

        try:
            # 根据任务的通知设置决定是否发送通知
            is_notice = StatusEnum.FAIL.value  # 默认不发送通知 (0)
            if task.is_notice == StatusEnum.SUCCESS.value and task.notice_group:
                # 如果任务启用了通知且有通知组，根据报告状态决定是否通知
                # 失败状态(ERROR=1) 或 警告状态(WARNING=2) 时发送通知
                if status in [MonitoringLogStatusEnum.ERROR.value, MonitoringLogStatusEnum.WARNING.value]:
                    is_notice = StatusEnum.SUCCESS.value  # 需要发送通知 (1)
                    # TODO: 在这里可以调用通知服务发送实际通知
                    # from src.apps.system.services.notice import NoticeMain
                    # NoticeMain.notice_main(task.notice_group.id, task.id)

            # 创建报告记录
            report = MonitoringReport.objects.create(
                task=task,
                status=status,
                msg=msg,
                send_text=detail if detail else None,
                is_notice=is_notice,
            )
            serializer = MonitoringReportSerializers(report)
            return ResponseData.success(RESPONSE_MSG_0153, serializer.data)
        except Exception as e:
            report_system_error(e, source=SystemErrorEventSource.HTTP, request=request)
            return ResponseData.fail(MONITORING_REPORT_CREATE_FAILED)
