# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.task_center.models import TimeTasks
from src.apps.user.formatters import format_user


class TimeTasksSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TimeTasks
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('update_user')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['update_user'] = (
            format_user(instance.update_user)
            if instance.update_user_id
            else None
        )
        return data
