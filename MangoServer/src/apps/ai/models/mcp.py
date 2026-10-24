# -*- coding: utf-8 -*-
from django.db import models

from src.apps.ai.enums import (
    AiMcpAuthTypeEnum,
    AiMcpStatusEnum,
    AiMcpToolRiskLevelEnum,
    AiMcpTransportTypeEnum,
    AiMcpUseTypeEnum,
)
from src.apps.ai.exceptions import (
    AI_MCP_SERVER_IMPORTED_API_BOUND,
    AI_MCP_TOOL_IMPORTED_API_BOUND,
    AiError,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


class AiMcpServer(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct,
        to_field="id",
        verbose_name="项目/产品",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    module = models.ForeignKey(
        to=ProductModule,
        to_field="id",
        verbose_name="模块",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    type = models.SmallIntegerField(
        verbose_name="MCP使用范围",
        choices=AiMcpUseTypeEnum.choices(),
        default=AiMcpUseTypeEnum.PLATFORM.value,
        db_index=True,
    )
    name = models.CharField(verbose_name="MCP服务名称", max_length=128)
    server_url = models.CharField(verbose_name="服务地址", max_length=1024)
    transport_type = models.SmallIntegerField(
        verbose_name="传输类型",
        choices=AiMcpTransportTypeEnum.choices(),
        default=AiMcpTransportTypeEnum.STREAMABLE_HTTP.value,
    )
    auth_type = models.SmallIntegerField(
        verbose_name="鉴权方式",
        choices=AiMcpAuthTypeEnum.choices(),
        default=AiMcpAuthTypeEnum.NONE.value,
    )
    auth_config = models.JSONField(verbose_name="鉴权配置", default=dict, blank=True)
    description = models.CharField(verbose_name="描述", max_length=512, null=True, blank=True)
    prompt = models.TextField(verbose_name="MCP使用提示词")
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=AiMcpStatusEnum.choices(),
        default=AiMcpStatusEnum.ENABLED.value,
        db_index=True,
    )
    last_sync_time = models.DateTimeField(verbose_name="最近同步时间", null=True, blank=True)
    last_test_time = models.DateTimeField(verbose_name="最近测试时间", null=True, blank=True)
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_mcp_server_create_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_mcp_server_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "ai_mcp_server"
        ordering = ["-id"]

    def delete(self, *args, **kwargs):
        from src.apps.auto_api.models import ApiInfoMcpBinding, ApiInfoMcpConfig

        if (
                ApiInfoMcpBinding.objects.filter(mcp_tool__server=self).exists()
                or ApiInfoMcpConfig.objects.filter(mcp_tool__server=self).exists()
        ):
            raise AiError(AI_MCP_SERVER_IMPORTED_API_BOUND)
        super().delete(*args, **kwargs)


class AiMcpTool(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    server = models.ForeignKey(to="AiMcpServer", to_field="id", on_delete=models.CASCADE)
    project_product = models.ForeignKey(
        to=ProjectProduct,
        to_field="id",
        verbose_name="项目/产品",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    module = models.ForeignKey(
        to=ProductModule,
        to_field="id",
        verbose_name="模块",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    type = models.SmallIntegerField(
        verbose_name="MCP使用范围",
        choices=AiMcpUseTypeEnum.choices(),
        default=AiMcpUseTypeEnum.PLATFORM.value,
        db_index=True,
    )
    name = models.CharField(verbose_name="工具名称", max_length=256, db_index=True)
    title = models.CharField(verbose_name="展示名称", max_length=256, null=True, blank=True)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    input_schema = models.JSONField(verbose_name="入参结构", default=dict, blank=True)
    output_schema = models.JSONField(verbose_name="出参结构", default=dict, blank=True)
    tool_type = models.CharField(verbose_name="类型", max_length=32, default="tool")
    risk_level = models.SmallIntegerField(
        verbose_name="风险等级",
        choices=AiMcpToolRiskLevelEnum.choices(),
        default=AiMcpToolRiskLevelEnum.READ.value,
        db_index=True,
    )
    write_operation = models.BooleanField(verbose_name="是否写操作", default=False)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    require_confirm = models.BooleanField(verbose_name="是否需要确认", default=False)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_mcp_tool_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "ai_mcp_tool"
        ordering = ["server_id", "name"]
        unique_together = ("server", "name", "tool_type")

    def delete(self, *args, **kwargs):
        from src.apps.auto_api.models import ApiInfoMcpBinding, ApiInfoMcpConfig

        if ApiInfoMcpBinding.objects.filter(mcp_tool=self).exists() or ApiInfoMcpConfig.objects.filter(
                mcp_tool=self).exists():
            raise AiError(AI_MCP_TOOL_IMPORTED_API_BOUND)
        super().delete(*args, **kwargs)


class AiMcpToolSnapshot(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    server = models.ForeignKey(to="AiMcpServer", to_field="id", related_name="tool_snapshots", on_delete=models.CASCADE)
    tool = models.ForeignKey(to="AiMcpTool", to_field="id", related_name="snapshots", on_delete=models.CASCADE)
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True, db_index=True)
    protocol_version = models.CharField(verbose_name="协议版本", max_length=64, null=True, blank=True)
    input_schema = models.JSONField(verbose_name="入参结构", default=dict, blank=True)
    output_schema = models.JSONField(verbose_name="出参结构", default=dict, blank=True)
    schema_hash = models.CharField(verbose_name="Schema哈希", max_length=128, db_index=True)
    is_available = models.BooleanField(verbose_name="是否可用", default=True, db_index=True)
    sync_error = models.TextField(verbose_name="同步错误", null=True, blank=True)

    class Meta:
        db_table = "ai_mcp_tool_snapshot"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["server", "tool", "test_env", "-id"], name="idx_mcp_tool_snapshot_env"),
        ]
