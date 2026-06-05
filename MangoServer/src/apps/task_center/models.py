from django.db import models

from src.apps.auto_system.models import Tasks, TestSuite, TimeTasks
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum


class ScheduleFire(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    time_task = models.ForeignKey(
        to=TimeTasks,
        to_field="id",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="定时策略",
    )
    task = models.ForeignKey(
        to=Tasks,
        to_field="id",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="定时任务",
    )
    task_name = models.CharField(verbose_name="任务名称快照", max_length=128, null=True)
    fire_key = models.CharField(verbose_name="触发唯一键", max_length=191, unique=True, null=True)
    planned_at = models.DateTimeField(verbose_name="计划触发时间", db_index=True)
    fired_at = models.DateTimeField(verbose_name="实际触发时间", null=True)
    source_type = models.SmallIntegerField(
        verbose_name="触发类型",
        choices=ScheduleFireSourceTypeEnum.choices(),
        default=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
        db_index=True,
    )
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=ScheduleFireStatusEnum.choices(),
        default=ScheduleFireStatusEnum.PENDING.value,
        db_index=True,
    )
    test_suite = models.ForeignKey(
        to=TestSuite,
        to_field="id",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="测试套",
    )
    trigger_node = models.CharField(verbose_name="触发节点", max_length=128, null=True)
    dispatcher_node = models.CharField(verbose_name="分发节点", max_length=128, null=True)
    error_message = models.TextField(verbose_name="错误信息", null=True)
    extra_data = models.JSONField(verbose_name="扩展数据", default=dict)

    class Meta:
        db_table = 'schedule_fire'
        ordering = ['-planned_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['time_task', 'task', 'planned_at', 'source_type'],
                name='uniq_schedule_fire_task_plan_type',
            )
        ]
        indexes = [
            models.Index(fields=['status', 'planned_at'], name='idx_fire_status_plan'),
            models.Index(fields=['task', 'planned_at'], name='idx_fire_task_plan'),
        ]
