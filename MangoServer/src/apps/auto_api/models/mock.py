from django.db import models
from django.utils import timezone

from src.apps.test_center.models import ProjectProduct
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiMockConfig(models.Model):
    """测试平台提供的单个 HTTP Mock 接口配置。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct,
        to_field="id",
        related_name="api_mock_configs",
        on_delete=models.PROTECT,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_mock_config_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(verbose_name="Mock接口名称", max_length=128)
    mock_key = models.CharField(verbose_name="Mock URL标识", max_length=64, unique=True)
    description = models.CharField(verbose_name="接口说明", max_length=500, blank=True, default="")
    method = models.SmallIntegerField(verbose_name="HTTP请求方法")
    path = models.CharField(verbose_name="请求路径模板", max_length=512)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    record_call_log = models.BooleanField(verbose_name="是否记录普通调用", default=False)
    config = models.JSONField(
        verbose_name="断言与响应配置",
        default=dict, blank=True,
        help_text="固定结构：assertions、rules、default_response",
    )

    class Meta:
        db_table = "api_mock_config"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["project_product", "enabled"], name="api_mock_product_enabled_idx"),
        ]


class ApiMockRequestLog(models.Model):
    """Mock 调用明细；普通调用可关闭，断言失败与平台异常强制记录。"""

    create_time = models.DateTimeField(verbose_name="调用时间", default=timezone.now, db_index=True)
    mock_config = models.ForeignKey(
        to="ApiMockConfig",
        to_field="id",
        related_name="request_logs",
        on_delete=models.CASCADE,
    )
    trace_id = models.CharField(verbose_name="Trace ID", max_length=64, db_index=True)
    rule_key = models.CharField(verbose_name="命中规则Key", max_length=64, null=True, blank=True)
    method = models.SmallIntegerField(verbose_name="HTTP请求方法")
    request_path = models.CharField(verbose_name="实际请求路径", max_length=1024)
    request_data = models.JSONField(verbose_name="请求摘要", default=dict, blank=True)
    assertion_passed = models.BooleanField(verbose_name="请求断言是否通过", default=True, db_index=True)
    assertion_results = models.JSONField(verbose_name="请求断言结果", default=list, blank=True)
    response_status = models.PositiveSmallIntegerField(verbose_name="响应状态码", null=True, blank=True)
    response_data = models.JSONField(verbose_name="响应摘要", default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(verbose_name="处理耗时毫秒", default=0)
    error_message = models.CharField(verbose_name="平台异常", max_length=1000, blank=True, default="")
    client_ip = models.GenericIPAddressField(verbose_name="调用方IP", null=True, blank=True)

    class Meta:
        db_table = "api_mock_request_log"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["mock_config", "-create_time"], name="api_mock_log_config_time_idx"),
            models.Index(
                fields=["mock_config", "assertion_passed", "-create_time"],
                name="api_mock_log_assert_time_idx",
            ),
        ]
