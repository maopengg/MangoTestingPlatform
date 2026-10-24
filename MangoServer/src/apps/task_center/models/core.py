from django.db import models
from mangotools.enums import TaskEnum

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.enums import (
    ScheduleFireSourceTypeEnum,
    ScheduleFireStatusEnum,
    WorkbenchTodoEventTypeEnum,
    WorkbenchTodoSeverityEnum,
    WorkbenchTodoSourceTypeEnum,
    WorkbenchTodoStatusEnum,
)
from src.apps.task_center.models.scheduling import ScheduledTaskGroup, Tasks, TimeTasks
from src.apps.test_center.models import NoticeGroup, ProductModule, ProjectProduct, TestSuite
from src.apps.user.models import User


class ScheduledTaskGroupExecution(models.Model):
    """同一任务组在一个计划时间、环境下的运行批次。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    execution_key = models.CharField(verbose_name="执行批次唯一键", max_length=191, unique=True)
    task_group = models.ForeignKey(
        to=ScheduledTaskGroup,
        to_field="id",
        related_name="executions",
        on_delete=models.SET_NULL,
        null=True,
    )
    task_group_name = models.CharField(verbose_name="任务组名称快照", max_length=64)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    time_task = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    planned_at = models.DateTimeField(verbose_name="计划触发时间", db_index=True)
    expected_count = models.PositiveIntegerField(verbose_name="预期子任务数", default=0)
    completed_count = models.PositiveIntegerField(verbose_name="已完成子任务数", default=0)
    status = models.SmallIntegerField(verbose_name="执行状态", default=TaskEnum.STAY_BEGIN.value, db_index=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", default=0)
    notice_group = models.ForeignKey(to=NoticeGroup, to_field="id", on_delete=models.SET_NULL, null=True)
    fail_notice = models.SmallIntegerField(verbose_name="仅失败通知", default=0)
    notice_status = models.SmallIntegerField(
        verbose_name="通知状态",
        default=TestSuiteNoticeEnum.NOT_SENT.value,
        db_index=True,
    )
    finished_at = models.DateTimeField(verbose_name="完成时间", null=True, blank=True)

    class Meta:
        db_table = "scheduled_task_group_execution"
        ordering = ["-planned_at", "-id"]
        indexes = [
            models.Index(fields=["task_group", "planned_at"], name="idx_group_exec_plan"),
            models.Index(fields=["status", "notice_status"], name="idx_group_exec_notice"),
        ]


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
    group_execution = models.ForeignKey(
        to=ScheduledTaskGroupExecution,
        to_field="id",
        related_name="fires",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="任务组执行批次",
    )
    task_name = models.CharField(verbose_name="任务名称快照", max_length=128, null=True, blank=True)
    fire_key = models.CharField(verbose_name="触发唯一键", max_length=191, unique=True, null=True, blank=True)
    planned_at = models.DateTimeField(verbose_name="计划触发时间", db_index=True)
    fired_at = models.DateTimeField(verbose_name="实际触发时间", null=True, blank=True)
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
    trigger_node = models.CharField(verbose_name="触发节点", max_length=128, null=True, blank=True)
    dispatcher_node = models.CharField(verbose_name="分发节点", max_length=128, null=True, blank=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    extra_data = models.JSONField(verbose_name="扩展数据", default=dict, blank=True)

    class Meta:
        db_table = 'schedule_fire'
        ordering = ['-planned_at', '-id']
        # 触发去重由 fire_key（source_type + 业务键 + 计划分钟）唯一索引保证，测试套业务键
        # 已包含环境。不要再按 (time_task, task, planned_at, source_type) 建唯一约束：
        # 同一任务同一分钟的不同环境会共用前三个字段，第二条触发记录会被误判为重复。
        indexes = [
            models.Index(fields=['status', 'planned_at'], name='idx_fire_status_plan'),
            models.Index(
                fields=['status', 'source_type', '-update_time', '-id'],
                name='idx_fire_error_recent',
            ),
            models.Index(fields=['task', 'planned_at'], name='idx_fire_task_plan'),
        ]


class WorkbenchTodo(models.Model):
    """首页风险待办；details 按 source_type 保存固定来源快照。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    event_key = models.CharField(verbose_name="事件唯一键", max_length=191, unique=True)
    source_type = models.SmallIntegerField(
        verbose_name="来源类型",
        choices=WorkbenchTodoSourceTypeEnum.choices(),
        db_index=True,
    )
    event_type = models.SmallIntegerField(
        verbose_name="事件类型",
        choices=WorkbenchTodoEventTypeEnum.choices(),
        db_index=True,
    )
    source_id = models.BigIntegerField(verbose_name="来源记录ID", db_index=True)
    project_product = models.ForeignKey(
        to=ProjectProduct,
        to_field="id",
        on_delete=models.PROTECT,
    )
    module = models.ForeignKey(
        to=ProductModule,
        to_field="id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    severity = models.SmallIntegerField(
        verbose_name="严重程度",
        choices=WorkbenchTodoSeverityEnum.choices(),
        db_index=True,
    )
    status = models.SmallIntegerField(
        verbose_name="处理状态",
        choices=WorkbenchTodoStatusEnum.choices(),
        default=WorkbenchTodoStatusEnum.PENDING.value,
        db_index=True,
    )
    title = models.CharField(verbose_name="待办标题", max_length=191)
    summary = models.TextField(verbose_name="待办摘要")
    due_at = models.DateTimeField(verbose_name="到期时间", null=True, blank=True, db_index=True)
    occurred_at = models.DateTimeField(verbose_name="发生时间", db_index=True)
    details = models.JSONField(verbose_name="来源快照", default=dict, blank=True)
    handled_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="handled_workbench_todos",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    handled_at = models.DateTimeField(verbose_name="处理时间", null=True, blank=True)
    handle_note = models.TextField(verbose_name="处理说明", null=True, blank=True)

    class Meta:
        db_table = "workbench_todo"
        ordering = ["-severity", "due_at", "-occurred_at", "-id"]
        indexes = [
            models.Index(
                fields=["status", "project_product", "severity"],
                name="idx_todo_status_product_level",
            ),
            models.Index(
                fields=["source_type", "source_id", "event_type"],
                name="idx_todo_source_event",
            ),
        ]
