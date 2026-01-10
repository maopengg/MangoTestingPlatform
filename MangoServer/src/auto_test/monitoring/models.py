# -*- coding: utf-8 -*-
# @Description: 预警监控任务模型
from django.db import models

from src.auto_test.auto_system.models import ProjectProduct, NoticeGroup
from src.enums.monitoring_enum import MonitoringTaskStatusEnum, MonitoringLogStatusEnum
from src.enums.tools_enum import StatusEnum

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class MonitoringTask(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True, default=None)
    script_content = models.TextField()
    script_path = models.CharField(max_length=512, blank=True, null=True, default=None)
    log_path = models.CharField(max_length=512, blank=True, null=True, default=None)
    status = models.SmallIntegerField(verbose_name="状态", choices=MonitoringTaskStatusEnum.choices(),
                                      default=MonitoringTaskStatusEnum.QUEUED.value)
    pid = models.IntegerField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", choices=StatusEnum.choices(),
                                         default=StatusEnum.FAIL.value)
    notice_group = models.ForeignKey(to=NoticeGroup, to_field="id", verbose_name='通知组', on_delete=models.SET_NULL,
                                     null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'monitoring_task'
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.name}({self.status})'


class MonitoringReport(models.Model):
    """预警监控报告表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(
        to=MonitoringTask,
        to_field="id",
        on_delete=models.CASCADE,
        verbose_name="关联任务",
        related_name="reports"
    )
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=MonitoringLogStatusEnum.choices(),
        default=MonitoringLogStatusEnum.INFO.value
    )
    msg = models.TextField(verbose_name="消息内容", null=True, blank=True, default=None)
    send_text = models.TextField(verbose_name="详细信息", blank=True, null=True, default=None)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", choices=StatusEnum.choices(),
                                         default=StatusEnum.FAIL.value)

    class Meta:
        db_table = 'monitoring_report'
        ordering = ['-create_time']
        verbose_name = "预警监控报告"
        verbose_name_plural = "预警监控报告"

    def __str__(self):
        return f'{self.task.name} - {MonitoringLogStatusEnum.obj().get(self.status, "未知")} - {self.create_time}'
