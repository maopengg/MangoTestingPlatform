# -*- coding: utf-8 -*-
# @Description: 预警监控任务模型
from django.db import models

from src.auto_test.auto_system.models import ProjectProduct
from src.enums.monitoring_enum import MonitoringTaskStatusEnum


class MonitoringTask(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True, default=None)
    script_content = models.TextField()
    script_path = models.CharField(max_length=512, blank=True, null=True, default=None)
    log_path = models.CharField(max_length=512, blank=True, null=True, default=None)
    status = models.SmallIntegerField(verbose_name="状态", choices=MonitoringTaskStatusEnum.choices(), default=MonitoringTaskStatusEnum.QUEUED.value)
    pid = models.IntegerField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'monitoring_task'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.name}({self.status})'

