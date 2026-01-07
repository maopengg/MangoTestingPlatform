# -*- coding: utf-8 -*-
# @Description: 预警监控序列化
import os
import uuid
from django.conf import settings
from rest_framework import serializers

from .models import MonitoringTask


def _ensure_dirs():
    scripts_dir = os.path.join(settings.BASE_DIR, 'monitoring_scripts')
    logs_dir = os.path.join(settings.BASE_DIR, 'logs', 'monitoring')
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    return scripts_dir, logs_dir


class MonitoringTaskSerializer(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    stopped_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = MonitoringTask
        fields = '__all__'

    def create(self, validated_data):
        """
        支持 script_content / script_file 任一输入，写入文件后再落库。
        """
        request = self.context.get('request')
        scripts_dir, logs_dir = _ensure_dirs()

        # 取内容
        content = validated_data.pop('script_content', None)
        upload_file = validated_data.pop('script_file', None)
        if upload_file:
            content = upload_file.read().decode('utf-8')

        if not content:
            raise serializers.ValidationError('script_content 或 script_file 必须提供一个')

        file_id = uuid.uuid4().hex
        filename = f'{file_id}.py'
        script_path = os.path.join(scripts_dir, filename)
        log_path = os.path.join(logs_dir, f'{file_id}.log')

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)

        validated_data.update({
            'script_path': script_path,
            'log_path': log_path,
            'status': MonitoringTask.Status.QUEUED,
        })
        return super().create(validated_data)


class MonitoringTaskWriteSerializer(MonitoringTaskSerializer):
    script_content = serializers.CharField(required=False, allow_blank=True)
    script_file = serializers.FileField(required=False, allow_empty_file=False)

    class Meta(MonitoringTaskSerializer.Meta):
        fields = MonitoringTaskSerializer.Meta.fields + ['script_content', 'script_file']

