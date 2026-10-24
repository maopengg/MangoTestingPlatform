from rest_framework import serializers

from src.apps.ai.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.ai.enums import AiMcpStatusEnum
from src.apps.ai.models import AiMcpServer
from src.apps.ai.services.core import mask_sensitive
from src.apps.ai.services.mcp_server import AiMcpServerMutationService
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user


class AiMcpServerSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_test_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    is_builtin = serializers.SerializerMethodField()
    is_builtin_local = serializers.SerializerMethodField()
    is_builtin_manual = serializers.SerializerMethodField()
    is_connected = serializers.SerializerMethodField()

    class Meta:
        model = AiMcpServer
        fields = "__all__"

    def validate_prompt(self, value):
        if not str(value or "").strip():
            raise serializers.ValidationError("MCP使用提示词不能为空")
        return str(value).strip()

    def validate(self, attrs):
        payload = {
            key: getattr(value, "id", value)
            for key, value in attrs.items()
        }
        errors = AiMcpServerMutationService._validate(self.instance, payload)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def setup_eager_loading(queryset):
        return ProductModuleService.with_full_paths(queryset, 'module').select_related(
            "project_product",
            "create_user",
            "update_user",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["auth_config"] = mask_sensitive(data.get("auth_config") or {})
        data["project_product"] = format_project_product(
            instance.project_product) if instance.project_product_id else None
        data["module"] = format_product_module(instance.module) if instance.module_id else None
        data["create_user"] = format_user(instance.create_user) if instance.create_user_id else None
        data["update_user"] = format_user(instance.update_user) if instance.update_user_id else None
        return data

    @staticmethod
    def get_is_builtin(instance):
        return bool((instance.auth_config or {}).get("builtin"))

    @staticmethod
    def get_is_builtin_local(instance):
        return bool((instance.auth_config or {}).get("builtin_local"))

    @staticmethod
    def get_is_builtin_manual(instance):
        return bool((instance.auth_config or {}).get("builtin_manual"))

    @staticmethod
    def get_is_connected(instance):
        return bool(
            instance.status == AiMcpStatusEnum.ENABLED.value
            and instance.last_test_time
            and not instance.last_error
        )
