# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.auto_api.api.serializers.api_case_mutation import ApiCaseSerializers
from src.apps.auto_api.api.serializers.api_info_mutation import ApiInfoSerializers
from src.apps.auto_api.models import ApiCaseDetailed
from src.apps.auto_api.schemas.recovery import ApiStepExecutionConfig
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ApiCaseDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    def validate_execution_config(self, value):
        return ApiStepExecutionConfig.parse_config(value).model_dump(exclude_defaults=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = serializers.SerializerMethodField()
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'

    @staticmethod
    def get_api_info(instance):
        data = ApiInfoSerializers(instance.api_info).data
        if instance.pinned_api_info_revision_id:
            runtime_payload = ApiInfoRuntimeService.normalize_payload(
                instance.pinned_api_info_revision.payload,
            )
        else:
            runtime_payload = ApiInfoRuntimeService.current_payload(instance.api_info)
        for field in ('method', 'url', 'protocol_type', 'body_type'):
            data[field] = runtime_payload.get(field)
        return data

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'api_info',
            'pinned_api_info_revision',
            'update_user')
        return queryset
