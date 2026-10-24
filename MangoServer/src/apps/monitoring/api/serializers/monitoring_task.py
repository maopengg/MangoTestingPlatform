# -*- coding: utf-8 -*-
import os
import uuid

from rest_framework import serializers

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.models import MonitoringTask
from src.apps.test_center.formatters.related import format_notice_group
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


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
        log_path = os.path.join('monitoring', 'logs', f'{file_id}.log').replace('\\', '/')  # 统一使用 / 作为路径分隔符

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
    test_env_display = serializers.SerializerMethodField()
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    notice_group = RelatedObjectField(formatter=format_notice_group, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = MonitoringTask
        fields = '__all__'

    def get_status_display(self, obj):
        """返回状态的中文标签"""
        return MonitoringTaskStatusEnum.obj().get(obj.status, '未知')

    @staticmethod
    def get_test_env_display(obj):
        from src.apps.test_center.enums.environment import EnvironmentEnum
        return EnvironmentEnum.obj().get(obj.test_env) if obj.test_env is not None else None

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'notice_group',
            'update_user',
        )
        return queryset
