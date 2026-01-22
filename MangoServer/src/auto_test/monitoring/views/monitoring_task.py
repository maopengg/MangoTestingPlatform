# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2026-01-06
# @Author : 
import os
import uuid

from django.conf import settings
from django.http import FileResponse
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.views.notice_group import NoticeGroupSerializers
from src.auto_test.monitoring.models import MonitoringTask
from src.auto_test.monitoring.service import runner
from src.enums.monitoring_enum import MonitoringTaskStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import (
    RESPONSE_MSG_0142, RESPONSE_MSG_0143, RESPONSE_MSG_0144,
    RESPONSE_MSG_0145, RESPONSE_MSG_0146, RESPONSE_MSG_0147,
    RESPONSE_MSG_0148, RESPONSE_MSG_0149, RESPONSE_MSG_0150
)


def _ensure_dirs():
    scripts_dir = os.path.join(settings.BASE_DIR, 'monitoring_scripts')
    logs_dir = os.path.join(settings.BASE_DIR, 'logs', 'monitoring')
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    return scripts_dir, logs_dir


class MonitoringTaskSerializers(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    stopped_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    log_path = serializers.CharField(read_only=True)  # 由 create 方法自动生成，不需要用户输入
    script_content = serializers.CharField(required=False, allow_blank=True, write_only=True)
    script_file = serializers.FileField(required=False, allow_empty_file=False, write_only=True)

    class Meta:
        model = MonitoringTask
        fields = '__all__'

    def validate(self, attrs):
        # POST 时检查 script_content 或 script_file
        if self.context.get('request') and self.context['request'].method == 'POST':
            if not attrs.get('script_content') and not attrs.get('script_file'):
                raise serializers.ValidationError('script_content 或 script_file 必须提供一个')
        return attrs

    def create(self, validated_data):
        """
        支持 script_content / script_file 任一输入，只保存代码内容到数据库，不写入文件。
        文件在执行时才生成，以支持多服务器部署。
        路径存储为相对路径（相对于 BASE_DIR），以支持跨平台部署。
        """
        # 取内容
        content = validated_data.pop('script_content', None)
        upload_file = validated_data.pop('script_file', None)
        if upload_file:
            content = upload_file.read().decode('utf-8')

        if not content:
            raise serializers.ValidationError('script_content 或 script_file 必须提供一个')

        # 生成日志路径（相对路径，文件路径在执行时生成）
        file_id = uuid.uuid4().hex
        log_path = os.path.join('logs', 'monitoring', f'{file_id}.log').replace('\\', '/')  # 统一使用 / 作为路径分隔符

        validated_data.update({
            'script_content': content,  # 保存代码内容到数据库
            'log_path': log_path,  # 存储相对路径
            'status': MonitoringTaskStatusEnum.QUEUED.value,
        })
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        更新时也支持更新 script_content
        """
        # 取内容
        content = validated_data.pop('script_content', None)
        upload_file = validated_data.pop('script_file', None)
        if upload_file:
            content = upload_file.read().decode('utf-8')

        # 如果提供了新的代码内容，更新它
        if content is not None:
            validated_data['script_content'] = content

        return super().update(instance, validated_data)


class MonitoringTaskSerializersC(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    stopped_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    status_display = serializers.SerializerMethodField()
    project_product = ProjectProductSerializersC(read_only=True)
    notice_group = NoticeGroupSerializers(read_only=True)

    class Meta:
        model = MonitoringTask
        fields = '__all__'

    def get_status_display(self, obj):
        """返回状态的中文标签"""
        return MonitoringTaskStatusEnum.obj().get(obj.status, '未知')

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related('project_product', 'notice_group')
        return queryset


class MonitoringTaskCRUD(ModelCRUD):
    model = MonitoringTask
    queryset = MonitoringTask.objects.all()
    serializer_class = MonitoringTaskSerializersC
    serializer = MonitoringTaskSerializers


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
        try:
            runner.start_task(task)
        except Exception as e:
            return ResponseData.fail(RESPONSE_MSG_0143, f'启动失败: {str(e)}')
        task.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0148, MonitoringTaskSerializers(task).data)

    @error_response('system')
    def stop(self, request: Request):
        task_id = request.data.get('id') or request.query_params.get('id')
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0142)
        try:
            runner.stop_task(task, update_status=True)
        except Exception as e:
            return ResponseData.fail(RESPONSE_MSG_0144, f'停止失败: {str(e)}')
        task.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0149, MonitoringTaskSerializers(task).data)

    @error_response('system')
    def logs(self, request: Request):
        task_id = request.query_params.get('id')
        limit = int(request.query_params.get('limit', 200))
        task = MonitoringTask.objects.filter(id=task_id).first()
        if not task:
            return ResponseData.fail(RESPONSE_MSG_0142)
        lines = runner.tail_log(task, limit=limit)
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
        
        # 将相对路径转换为绝对路径
        log_path = os.path.join(settings.BASE_DIR, task.log_path) if not os.path.isabs(task.log_path) else task.log_path
        
        if not os.path.exists(log_path):
            return ResponseData.fail(RESPONSE_MSG_0146)
        
        try:
            file = open(log_path, 'rb')
            filename = f'任务日志_{task.name}_{task.id}.log'
            response = FileResponse(file, as_attachment=True, filename=filename)
            return response
        except Exception as e:
            return ResponseData.fail(RESPONSE_MSG_0147, f'下载失败: {str(e)}')
