# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 预警监控报告视图
# @Time   : 2026-01-08
# @Author : 
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.monitoring.models import MonitoringReport, MonitoringTask
from src.enums.monitoring_enum import MonitoringLogStatusEnum
from src.enums.tools_enum import StatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import (
    RESPONSE_MSG_0151, RESPONSE_MSG_0152, RESPONSE_MSG_0153
)


class MonitoringReportSerializers(serializers.ModelSerializer):
    """报告序列化器（用于创建和更新）"""
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = MonitoringReport
        fields = '__all__'

    def validate_status(self, value):
        """验证状态值"""
        valid_statuses = [
            MonitoringLogStatusEnum.INFO.value,      # 0: 信息
            MonitoringLogStatusEnum.ERROR.value,     # 1: 失败
            MonitoringLogStatusEnum.WARNING.value,   # 2: 警告
            MonitoringLogStatusEnum.DEBUG.value,     # 3: 调试
        ]
        if value not in valid_statuses:
            raise serializers.ValidationError(f'状态值必须是 {valid_statuses} 之一')
        return value

    def validate_task_id(self, value):
        """验证任务是否存在"""
        if not MonitoringTask.objects.filter(id=value).exists():
            raise serializers.ValidationError('关联的任务不存在')
        return value


class MonitoringReportSerializersC(serializers.ModelSerializer):
    """报告序列化器（用于查询列表）"""
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    status_display = serializers.SerializerMethodField()
    task_name = serializers.SerializerMethodField()
    task_notice_group = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringReport
        fields = '__all__'

    def get_status_display(self, obj):
        """返回状态的中文标签"""
        return MonitoringLogStatusEnum.obj().get(obj.status, '未知')

    def get_task_name(self, obj):
        """返回任务名称"""
        return obj.task.name if obj.task else ''

    def get_task_notice_group(self, obj):
        """返回任务的通知组信息"""
        if obj.task and obj.task.notice_group:
            return {
                'id': obj.task.notice_group.id,
                'name': obj.task.notice_group.name,
            }
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related('task', 'task__notice_group')
        return queryset


class MonitoringReportCRUD(ModelCRUD):
    model = MonitoringReport
    queryset = MonitoringReport.objects.all()
    serializer_class = MonitoringReportSerializersC
    serializer = MonitoringReportSerializers


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
            MonitoringLogStatusEnum.INFO.value,      # 0: 信息
            MonitoringLogStatusEnum.ERROR.value,     # 1: 失败
            MonitoringLogStatusEnum.WARNING.value,   # 2: 警告
            MonitoringLogStatusEnum.DEBUG.value,     # 3: 调试
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
                    # from src.auto_test.auto_system.service.notice import NoticeMain
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
            return ResponseData.fail(RESPONSE_MSG_0151, f'创建报告失败: {str(e)}')


