# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.user.api.serializers.user import UserSerializers
from src.apps.user.models import UserLogs


class UserLogsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = UserLogs
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'user',
        )
        return queryset
