import uuid

from django.db import models
from django.utils import timezone

from src.apps.user.models import User


class SocketConnection(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    connection_id = models.UUIDField(verbose_name="连接ID", default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="socket_connections",
        on_delete=models.CASCADE,
    )
    client_type = models.SmallIntegerField(verbose_name="客户端类型", db_index=True)
    channel_name = models.CharField(verbose_name="通道名称", max_length=255)
    service_instance = models.CharField(verbose_name="服务实例", max_length=128, db_index=True)
    status = models.SmallIntegerField(verbose_name="连接状态", default=1, db_index=True)
    connected_at = models.DateTimeField(verbose_name="连接时间", default=timezone.now)
    last_seen_at = models.DateTimeField(verbose_name="最近心跳时间", default=timezone.now, db_index=True)
    disconnected_at = models.DateTimeField(verbose_name="断开时间", null=True, blank=True)
    is_open = models.BooleanField(verbose_name="开放状态", default=False)
    debug = models.BooleanField(verbose_name="调试日志状态", default=False)
    web_live_stream_supported = models.BooleanField(verbose_name="是否支持WEB直播画面", default=False)

    class Meta:
        db_table = "socket_connection"
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(
                fields=["user", "client_type", "status", "last_seen_at"],
                name="idx_socket_user_state",
            ),
            models.Index(
                fields=["service_instance", "status"],
                name="idx_socket_instance_state",
            ),
        ]


class ExecutorTask(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    message_key = models.CharField(verbose_name="业务幂等键", max_length=255, unique=True, null=True, blank=True)
    task_type = models.CharField(verbose_name="任务类型", max_length=64, db_index=True)
    status = models.CharField(verbose_name="任务状态", max_length=24, default="pending", db_index=True)
    created_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="created_executor_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    executor_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="executor_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    executor_connection = models.ForeignKey(
        to="SocketConnection",
        related_name="executor_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    target_executor_connection = models.ForeignKey(
        to="SocketConnection",
        related_name="target_executor_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    executor_mode = models.CharField(verbose_name="执行器模式", max_length=16)
    business_type = models.CharField(verbose_name="业务类型", max_length=32, db_index=True)
    business_id = models.BigIntegerField(verbose_name="业务ID", null=True, blank=True, db_index=True)
    workspace_id = models.CharField(verbose_name="实时工作区ID", max_length=64, null=True, blank=True, db_index=True)
    payload = models.JSONField(verbose_name="任务请求", default=dict, blank=True)
    result_data = models.JSONField(verbose_name="任务结果", null=True, blank=True)
    progress_data = models.JSONField(verbose_name="任务进度", default=dict, blank=True)
    error_code = models.CharField(verbose_name="错误码", max_length=64, null=True, blank=True)
    error_message = models.CharField(verbose_name="错误说明", max_length=2048, null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(verbose_name="重试次数", default=0)
    available_at = models.DateTimeField(verbose_name="下次领取时间", default=timezone.now, db_index=True)
    lease_expires_at = models.DateTimeField(verbose_name="领取租约到期时间", null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(verbose_name="开始执行时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="完成时间", null=True, blank=True)
    schedule_deadline = models.DateTimeField(verbose_name="调度截止时间", null=True, blank=True, db_index=True)
    expired_at = models.DateTimeField(verbose_name="过期时间", db_index=True)
    cancel_requested_at = models.DateTimeField(verbose_name="请求取消时间", null=True, blank=True)

    class Meta:
        db_table = "executor_task"
        ordering = ["id"]
        indexes = [
            models.Index(fields=['task_type', 'status', 'available_at', 'id'], name='idx_exec_type_due'),
            models.Index(
                fields=["status", "available_at", "schedule_deadline"],
                name="idx_executor_task_pending",
            ),
            models.Index(
                fields=["executor_user", "status", "available_at"],
                name="idx_executor_task_user",
            ),
            models.Index(
                fields=["executor_connection", "status", "lease_expires_at"],
                name="idx_executor_task_conn",
            ),
            models.Index(
                fields=["target_executor_connection", "status", "available_at"],
                name="idx_executor_task_target",
            ),
            models.Index(
                fields=["business_type", "business_id", "created_by", "create_time"],
                name="idx_executor_task_business",
            ),
            models.Index(
                fields=["status", "lease_expires_at", "expired_at"],
                name="idx_executor_task_lease",
            ),
            models.Index(
                fields=["workspace_id", "status"],
                name="idx_executor_task_workspace",
            ),
        ]
