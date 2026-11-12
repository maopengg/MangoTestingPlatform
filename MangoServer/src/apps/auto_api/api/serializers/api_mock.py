from rest_framework import serializers
from django.db import transaction

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    MOCK_API_CREATE_NOT_ALLOWED,
)
from src.apps.auto_api.models import ApiMockConfig, ApiMockRequestLog
from src.apps.auto_api.services.mock.mock_request_decryption import MockRequestDecryptionService
from src.apps.auto_api.services.mock.mock_runtime import MOCK_SUPPORTED_METHODS, MockConfigValidator
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class ApiMockConfigSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ApiMockConfig
        fields = "__all__"

    def validate_mock_key(self, value):
        value = MockConfigValidator.validate_mock_key(value)
        if self.instance is not None and value != self.instance.mock_key:
            raise AutoApiError(MOCK_API_CREATE_NOT_ALLOWED)
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        from src.apps.auto_api.services.callbacks.callback import ApiCallbackService
        from src.apps.auto_api.models import ApiCaseCallbackRun
        from src.apps.auto_api.enums.callback import CallbackRunStatus
        from src.apps.auto_api.exceptions import API_CALLBACK_CONFIG_INVALID
        from django.utils import timezone
        instance = ApiMockConfig.objects.select_for_update().get(pk=instance.pk)
        if ApiCallbackService.enabled():
            active = ApiCaseCallbackRun.objects.filter(mock_config=instance, status=CallbackRunStatus.WAITING,
                                                      deadline__gt=timezone.now())
            if active.exists():
                changed = any(key in validated_data and validated_data[key] != getattr(instance, key)
                              for key in ('path', 'method', 'config', 'project_product'))
                if changed:
                    raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('存在活动回调验证，结束后再修改Mock配置',))
                if validated_data.get('enabled') is False:
                    ApiCallbackService.cancel(list(active.values_list('pk', flat=True)), message='Mock已停用')
        return super().update(instance, validated_data)

    def validate_path(self, value):
        return MockConfigValidator.validate_path(value)

    def validate_method(self, value):
        if value not in MOCK_SUPPORTED_METHODS:
            raise serializers.ValidationError("Mock接口只支持标准HTTP请求方法")
        return value

    def validate_config(self, value):
        normalized = dict(value)
        if "methods" not in normalized:
            fallback_method = self.initial_data.get("method")
            if fallback_method is None and self.instance is not None:
                fallback_method = self.instance.method
            normalized["methods"] = [int(fallback_method)] if fallback_method is not None else []
        existing_config = self.instance.config if self.instance is not None else None
        normalized["request_decryption"] = MockRequestDecryptionService.normalize_for_storage(
            value.get("request_decryption"),
            existing_config,
        )
        return MockConfigValidator.validate_config(normalized)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        config = attrs.get("config")
        if config is not None:
            methods = config.get("methods") or []
            attrs["method"] = methods[0] if methods else MethodEnum.GET.value
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        config = dict(data.get("config") or {})
        if "methods" not in config:
            config["methods"] = [instance.method]
        config["request_decryption"] = MockRequestDecryptionService.editable_config(
            (instance.config or {}).get("request_decryption")
        )
        data["config"] = config
        return data


class ApiMockConfigListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    method_name = serializers.SerializerMethodField()

    class Meta:
        model = ApiMockConfig
        exclude = ("config",)

    @staticmethod
    def get_method_name(obj):
        config = obj.config or {}
        methods = config.get("methods") if "methods" in config else [obj.method]
        if not methods:
            return "全部"
        return " / ".join(MethodEnum.obj().get(method, "-") for method in methods)

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(queryset.select_related(
            "project_product",
            "project_product__project",
            "update_user",
        ))


class ApiMockRequestLogSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    method_name = serializers.SerializerMethodField()

    class Meta:
        model = ApiMockRequestLog
        exclude = ('callback_run', 'callback_evidence')

    @staticmethod
    def get_method_name(obj):
        return MethodEnum.obj().get(obj.method, "-")
