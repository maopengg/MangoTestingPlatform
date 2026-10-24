# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.api.serializers.mcp_server_mutation import AiMcpServerSerializer
from src.apps.ai.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.ai.enums import AiMcpUseTypeEnum
from src.apps.ai.models import AiMcpTool
from src.apps.ai.services.core import McpService
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user


class AiMcpToolSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    category = serializers.SerializerMethodField()
    category_title = serializers.SerializerMethodField()
    api_info_binding = serializers.SerializerMethodField()

    class Meta:
        model = AiMcpTool
        fields = "__all__"

    def validate(self, attrs):
        project_product = attrs.get("project_product") or getattr(self.instance, "project_product", None)
        module = attrs.get("module") or getattr(self.instance, "module", None)
        effective_project_product = project_product or getattr(
            attrs.get("server") or getattr(self.instance, "server", None),
            "project_product",
            None,
        )
        if module and effective_project_product and module.project_product_id != effective_project_product.id:
            raise serializers.ValidationError({"module": "模块不属于当前项目/产品"})
        if module and not effective_project_product:
            raise serializers.ValidationError({"project_product": "选择模块时必须选择项目/产品"})
        target_type = attrs.get("type", getattr(self.instance, "type", None))
        server = attrs.get("server") or getattr(self.instance, "server", None)
        if server and server.type == AiMcpUseTypeEnum.PLATFORM.value and target_type in {
            AiMcpUseTypeEnum.API_AUTOMATION.value,
            AiMcpUseTypeEnum.COMMON.value,
        }:
            raise serializers.ValidationError({"type": "平台调用范围的MCP服务下，Tool不能设置为API自动化或通用"})
        if (
                self.instance
                and target_type == AiMcpUseTypeEnum.PLATFORM.value
                and ApiQuerySelector.api_info_mcp_binding().filter(mcp_tool=self.instance).exists()
        ):
            raise serializers.ValidationError({"type": "MCP Tool已导入API自动化接口，不能改为平台调用"})
        return attrs

    @staticmethod
    def setup_eager_loading(queryset):
        return ProductModuleService.with_full_paths(
            queryset,
            'module',
            'server__module',
        ).select_related(
            "server",
            "project_product",
            "update_user",
            "api_info_binding",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["server"] = AiMcpServerSerializer(instance=instance.server).data if instance.server_id else None
        data["project_product"] = format_project_product(
            instance.project_product) if instance.project_product_id else None
        data["module"] = format_product_module(instance.module) if instance.module_id else None
        data["effective_project_product_id"] = instance.project_product_id or getattr(instance.server,
                                                                                      "project_product_id", None)
        data["effective_module_id"] = instance.module_id or getattr(instance.server, "module_id", None)
        data["update_user"] = format_user(instance.update_user) if instance.update_user_id else None
        return data

    @staticmethod
    def get_category(instance):
        return McpService.tool_category(instance.name)["key"]

    @staticmethod
    def get_category_title(instance):
        return McpService.tool_category(instance.name)["title"]

    @staticmethod
    def get_api_info_binding(instance):
        try:
            binding = getattr(instance, "api_info_binding", None)
        except Exception:
            binding = None
        if not binding:
            return None
        return {"api_info_id": binding.api_info_id}
