from django.db import models

from src.apps.test_center.models import FileData
from src.apps.test_center.models import ProjectProduct, ProductModule

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiInfoMcpBinding(models.Model):
    """MCP Tool 与 API 接口定义的当前编辑态映射。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    api_info = models.OneToOneField(
        to="ApiInfo",
        to_field="id",
        related_name="mcp_binding",
        verbose_name="接口定义",
        on_delete=models.CASCADE,
    )
    mcp_tool = models.OneToOneField(
        to="auto_ai.AiMcpTool",
        to_field="id",
        related_name="api_info_binding",
        verbose_name="MCP Tool",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "api_info_mcp_binding"
        ordering = ["-id"]


class ApiInfoMcpConfig(models.Model):
    """MCP Tool 协议配置当前编辑态。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    api_info = models.OneToOneField(
        to="ApiInfo",
        to_field="id",
        related_name="mcp_protocol_config",
        verbose_name="调用定义",
        on_delete=models.CASCADE,
    )
    mcp_tool = models.OneToOneField(
        to="auto_ai.AiMcpTool",
        to_field="id",
        related_name="api_info_protocol_config",
        verbose_name="MCP Tool",
        on_delete=models.PROTECT,
    )
    mcp_config = models.JSONField(verbose_name="MCP执行配置", null=True, blank=True)
    input_schema = models.JSONField(verbose_name="输入Schema快照", null=True, blank=True)
    output_schema = models.JSONField(verbose_name="输出Schema快照", null=True, blank=True)
    schema_hash = models.CharField(verbose_name="Schema Hash", max_length=128, null=True, blank=True)

    class Meta:
        db_table = "api_info_mcp_config"
        ordering = ["-id"]


class GrpcServiceDefinition(models.Model):
    """gRPC 服务定义，用于把 proto/descriptor 管理为可导入接口。"""

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
    name = models.CharField(verbose_name="服务名称", max_length=128)
    package = models.CharField(verbose_name="包名", max_length=255, null=True, blank=True)
    service_name = models.CharField(verbose_name="gRPC Service", max_length=255)
    proto_file = models.ForeignKey(
        to=FileData,
        to_field="id",
        related_name="grpc_proto_services",
        verbose_name="Proto文件",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    proto_content_hash = models.CharField(verbose_name="Proto内容Hash", max_length=128, null=True, blank=True,
                                          db_index=True)
    descriptor_file = models.ForeignKey(
        to=FileData,
        to_field="id",
        related_name="grpc_descriptor_services",
        verbose_name="Descriptor文件",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    reflection_enabled = models.BooleanField(verbose_name="是否启用Reflection", default=False)
    tls_enabled = models.BooleanField(verbose_name="是否启用TLS", default=False)
    status = models.SmallIntegerField(verbose_name="状态", default=1, db_index=True)
    last_sync_time = models.DateTimeField(verbose_name="最近同步时间", null=True, blank=True)
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True)

    class Meta:
        db_table = "grpc_service_definition"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["project_product", "service_name"], name="idx_grpc_service_product"),
        ]


class GrpcMethodDefinition(models.Model):
    """gRPC Method 定义；每个 Method 可导入为一条 ApiInfo。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    service = models.ForeignKey(
        to="GrpcServiceDefinition",
        to_field="id",
        related_name="methods",
        verbose_name="gRPC服务",
        on_delete=models.CASCADE,
    )
    name = models.CharField(verbose_name="方法名称", max_length=255)
    full_method = models.CharField(verbose_name="完整方法", max_length=512, db_index=True)
    request_message = models.CharField(verbose_name="请求Message", max_length=512)
    response_message = models.CharField(verbose_name="响应Message", max_length=512)
    client_streaming = models.BooleanField(verbose_name="客户端流", default=False)
    server_streaming = models.BooleanField(verbose_name="服务端流", default=False)
    request_json_schema = models.JSONField(verbose_name="请求JSON Schema", null=True, blank=True)
    response_json_schema = models.JSONField(verbose_name="响应JSON Schema", null=True, blank=True)
    default_request = models.JSONField(verbose_name="默认请求", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1, db_index=True)

    class Meta:
        db_table = "grpc_method_definition"
        ordering = ["service_id", "full_method"]
        constraints = [
            models.UniqueConstraint(fields=["service", "full_method"], name="uniq_grpc_method_full_method"),
        ]


class ApiInfoGrpcConfig(models.Model):
    """gRPC Method 协议配置当前编辑态。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    api_info = models.OneToOneField(
        to="ApiInfo",
        to_field="id",
        related_name="grpc_protocol_config",
        verbose_name="调用定义",
        on_delete=models.CASCADE,
    )
    grpc_service = models.ForeignKey(
        to="GrpcServiceDefinition",
        to_field="id",
        related_name="api_info_protocol_configs",
        verbose_name="gRPC服务",
        on_delete=models.PROTECT,
    )
    grpc_method = models.ForeignKey(
        to="GrpcMethodDefinition",
        to_field="id",
        related_name="api_info_protocol_configs",
        verbose_name="gRPC方法",
        on_delete=models.PROTECT,
    )
    full_method = models.CharField(verbose_name="完整方法", max_length=512)
    request_message = models.CharField(verbose_name="请求Message", max_length=512)
    response_message = models.CharField(verbose_name="响应Message", max_length=512)
    proto_hash = models.CharField(verbose_name="Proto Hash", max_length=128, null=True, blank=True)
    request_json_schema = models.JSONField(verbose_name="请求JSON Schema", null=True, blank=True)
    response_json_schema = models.JSONField(verbose_name="响应JSON Schema", null=True, blank=True)
    grpc_config = models.JSONField(verbose_name="gRPC执行配置", null=True, blank=True)

    class Meta:
        db_table = "api_info_grpc_config"
        ordering = ["-id"]
