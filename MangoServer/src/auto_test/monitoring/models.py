# -*- coding: utf-8 -*-
# @Description: 预警监控任务模型
from django.db import models
from django.utils import timezone


class MonitoringTask(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        STOPPED = 'stopped', 'Stopped'
        FAILED = 'failed', 'Failed'
        COMPLETED = 'completed', 'Completed'

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    script_content = models.TextField()  # 存储代码内容，多服务器部署时共享
    script_path = models.CharField(max_length=512, blank=True, default='')  # 执行时临时生成的文件路径
    log_path = models.CharField(max_length=512, blank=True, default='')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    pid = models.IntegerField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'monitoring_task'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.status})'

