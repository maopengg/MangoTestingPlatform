# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 预警监控报告视图
# @Time   : 2026-01-08
# @Author :
from rest_framework import serializers

from src.apps.monitoring.enums import MonitoringLogStatusEnum
from src.apps.monitoring.models import MonitoringReport, MonitoringTask


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
            MonitoringLogStatusEnum.INFO.value,  # 0: 信息
            MonitoringLogStatusEnum.ERROR.value,  # 1: 失败
            MonitoringLogStatusEnum.WARNING.value,  # 2: 警告
            MonitoringLogStatusEnum.DEBUG.value,  # 3: 调试
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
