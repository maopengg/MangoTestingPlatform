# -*- coding: utf-8 -*-
# @FileData: auto_test
# @Description:
# @Time   : 2024-05-17 12:32
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC
from src.apps.test_center.formatters.file_data import format_file_size
from src.apps.test_center.models import FileData
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class FileDataSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    test_file = serializers.FileField(use_url=False, allow_null=True, required=False, allow_empty_file=True)
    failed_screenshot = serializers.ImageField(use_url=False, allow_null=True, required=False)
    file_size_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'project_product',
            'project_product__project',
            'user',
            'update_user',
        ).prefetch_related('project_product__owners').order_by('-id')

    @staticmethod
    def get_file_size_display(obj):
        return format_file_size(obj.file_size)

    @staticmethod
    def get_user(obj):
        if not obj.user_id:
            return None
        return {
            'id': obj.user_id,
            'name': getattr(obj.user, 'name', ''),
            'username': getattr(obj.user, 'username', ''),
        }
