from django.db import models


class SystemErrorEvent(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    service_name = models.CharField(verbose_name="服务名称", max_length=64, db_index=True)
    source = models.CharField(verbose_name="异常来源", max_length=32, db_index=True)
    request_path = models.CharField(verbose_name="请求路径/任务入口", max_length=255, null=True, blank=True)
    exception_type = models.CharField(verbose_name="异常类型", max_length=128)
    message = models.CharField(verbose_name="异常摘要", max_length=500)
    traceback = models.TextField(verbose_name="异常堆栈", null=True, blank=True)
    fingerprint = models.CharField(verbose_name="异常指纹", max_length=64, unique=True)
    count = models.IntegerField(verbose_name="出现次数", default=1)
    last_seen_at = models.DateTimeField(verbose_name="最近出现时间", db_index=True)

    class Meta:
        db_table = "system_error_event"
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["service_name", "last_seen_at"], name="idx_error_service_seen"),
            models.Index(fields=["source", "last_seen_at"], name="idx_error_source_seen"),
        ]
