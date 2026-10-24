# -*- coding: utf-8 -*-
# @ProjectProduct: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.test_center.api.serializers.project import ProjectSerializers
from src.apps.test_center.models import ProjectProduct
from src.apps.user.formatters import format_user_simple
from src.apps.user.models import User
from src.common.validators.serializer_fields import RelatedObjectField


class ProjectProductSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    owners = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=True,
        allow_empty=False,
    )

    class Meta:
        model = ProjectProduct
        fields = '__all__'


class ProjectProductSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    owners = RelatedObjectField(formatter=format_user_simple, many=True, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ProjectProduct
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'update_user',
        ).prefetch_related('owners')
        return queryset
