# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.system.models import CacheData
from src.apps.test_center.formatters.related import format_project
from src.apps.test_center.formatters.related import format_test_object
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField

SECRET_VALUE_MASK = "__KEEP_SECRET__"


class CacheDataSerializersC(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.key == "EVALUATION_AI_PROFILES":
            from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
            data["value"] = EvaluationAiProfileService.masked(instance.value)
        return data

    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = RelatedObjectField(formatter=format_project, read_only=True)
    test_obj = RelatedObjectField(formatter=format_test_object, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = CacheData
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'test_obj',
            'update_user')
        return queryset
