from django.db import models


class ServiceHeartbeat(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    service_name = models.CharField(verbose_name="服务名称", max_length=64, db_index=True)
    instance_name = models.CharField(verbose_name="实例名称", max_length=128)
    host_name = models.CharField(verbose_name="主机名称", max_length=128)
    pod_name = models.CharField(verbose_name="Pod名称", max_length=128, null=True, blank=True)
    process_id = models.IntegerField(verbose_name="进程ID", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1, db_index=True)
    last_seen_at = models.DateTimeField(verbose_name="最近心跳时间", db_index=True)
    metadata = models.JSONField(verbose_name="扩展信息", default=dict, blank=True)

    class Meta:
        db_table = "service_heartbeat"
        ordering = ["service_name", "instance_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_name", "instance_name"],
                name="uniq_service_heartbeat_instance",
            )
        ]
        indexes = [
            models.Index(fields=["service_name", "last_seen_at"], name="idx_heartbeat_service_seen"),
            models.Index(fields=["status", "last_seen_at"], name="idx_heartbeat_status_seen"),
        ]
