from django.db import models

from src.apps.system.enums import TaskCaseVersionPolicyEnum
from src.apps.system.exceptions import (
    SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID,
    SystemError,
)
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum, ReportRetentionPolicyEnum
from src.apps.task_center.enums.schedule import ScheduledTaskGroupSyncStatusEnum
from src.apps.task_center.exceptions import SYSTEM_TASK_MODULE_CONFIG_TASK_DELETE_GENERATE_NOT_ALLOWED
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from django.apps import apps


class TimeTasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="time_tasks_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="定时策略名称", max_length=64, unique=True)
    cron = models.CharField(verbose_name="cron表达式", max_length=64)

    class Meta:
        db_table = 'time_tasks'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if Tasks.objects.filter(timing_strategies=self).exists():
            raise SystemError(SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class ScheduledTaskGroup(models.Model):
    """模块全量任务的公共配置；调度仍由拆分后的 Tasks 承担。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to="test_center.ProjectProduct", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="scheduled_task_group_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    name = models.CharField(verbose_name="任务组名称", max_length=64)
    test_envs = models.JSONField(verbose_name="测试环境", default=list, blank=True)
    case_types = models.JSONField(verbose_name="用例类型", default=list, blank=True)
    execution_scenes = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    case_people = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="scheduled_task_group_case_people",
        verbose_name="用例责任人",
        on_delete=models.PROTECT,
    )
    status = models.SmallIntegerField(verbose_name="任务组状态", default=0)
    timing_strategies = models.ManyToManyField(
        to="TimeTasks",
        related_name="scheduled_task_groups",
        verbose_name="定时策略",
    )
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", default=0)
    notice_group = models.ForeignKey(
        to="test_center.NoticeGroup",
        to_field="id",
        verbose_name="通知组",
        related_name="scheduled_task_groups",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    fail_notice = models.SmallIntegerField(verbose_name="只有失败发送", default=0)
    task_name_template = models.CharField(
        verbose_name="子任务名称模板",
        max_length=128,
        default="【${{任务组名称}}】${{模块名称}}",
    )
    revision = models.PositiveIntegerField(verbose_name="配置版本", default=1)
    sync_status = models.CharField(
        verbose_name="同步状态",
        max_length=16,
        choices=ScheduledTaskGroupSyncStatusEnum.choices(),
        default=ScheduledTaskGroupSyncStatusEnum.PENDING.value,
        db_index=True,
    )
    archived = models.BooleanField(verbose_name="是否归档", default=False, db_index=True)

    class Meta:
        db_table = 'scheduled_task_group'
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=['project_product', 'name'],
                name='scheduled_task_group_product_name_unique',
            ),
        ]


class Tasks(models.Model):
    report_retention_policy = models.CharField(verbose_name="报告保留策略", max_length=32,
        choices=ReportRetentionPolicyEnum.choices(), default=ReportRetentionPolicyEnum.ALL.value)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to="test_center.ProjectProduct", to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to="test_center.ProductModule", to_field="id", on_delete=models.PROTECT, null=True,
                               blank=True)
    task_group = models.ForeignKey(
        to="ScheduledTaskGroup",
        to_field="id",
        related_name="tasks",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    task_group_revision = models.PositiveIntegerField(
        verbose_name="任务组同步版本",
        null=True,
        blank=True,
    )
    update_user = models.ForeignKey(to=User, to_field="id", related_name="tasks_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    test_envs = models.JSONField(verbose_name="测试环境", default=list, blank=True)
    case_types = models.JSONField(verbose_name="用例类型", default=list, blank=True)
    execution_scenes = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    execution_scope = models.CharField(
        verbose_name="执行范围",
        max_length=32,
        choices=AutomationExecutionScopeEnum.choices(),
        default=AutomationExecutionScopeEnum.MANUAL.value,
        db_index=True,
    )
    name = models.CharField(verbose_name="任务名称", max_length=64)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)
    status = models.SmallIntegerField(verbose_name="任务状态", default=0)
    timing_strategies = models.ManyToManyField(
        to="TimeTasks",
        related_name="scheduled_tasks",
        verbose_name="定时策略",
    )
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", default=0)
    notice_group = models.ForeignKey(to="test_center.NoticeGroup", to_field="id", verbose_name='通知组',
                                     on_delete=models.SET_NULL,
                                     null=True)
    fail_notice = models.SmallIntegerField(verbose_name="只有失败发送", default=0)
    api_concurrency_limit = models.PositiveIntegerField(
        verbose_name="API执行并发",
        null=True,
        blank=True,
    )
    diagnostic_file_path = models.CharField(
        verbose_name="排查报告文件路径",
        max_length=500,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'tasks'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if self.task_group_id:
            raise SystemError(SYSTEM_TASK_MODULE_CONFIG_TASK_DELETE_GENERATE_NOT_ALLOWED)
        if TasksDetails.objects.filter(task=self).exists():
            raise SystemError(
                SYSTEM_SCHEDULING_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID)
        if apps.get_model("test_center", "TestSuite").objects.filter(tasks=self).exists():
            apps.get_model("test_center", "TestSuite").objects.filter(tasks=self).delete()
        super().delete(*args, **kwargs)


class ScheduledTaskGroupModule(models.Model):
    """任务组期望维护的模块，以及对应的实际定时任务。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task_group = models.ForeignKey(
        to="ScheduledTaskGroup",
        to_field="id",
        related_name="members",
        on_delete=models.CASCADE,
    )
    module = models.ForeignKey(to="test_center.ProductModule", to_field="id", on_delete=models.PROTECT)
    task = models.OneToOneField(
        to="Tasks",
        to_field="id",
        related_name="task_group_member",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    child_enabled = models.BooleanField(verbose_name="子任务是否启用", default=True)
    active = models.BooleanField(verbose_name="是否属于当前任务组范围", default=True, db_index=True)
    synced_revision = models.PositiveIntegerField(verbose_name="已同步版本", default=0)
    sync_status = models.CharField(
        verbose_name="同步状态",
        max_length=16,
        choices=ScheduledTaskGroupSyncStatusEnum.choices(),
        default=ScheduledTaskGroupSyncStatusEnum.PENDING.value,
        db_index=True,
    )
    sync_error = models.CharField(verbose_name="同步失败原因", max_length=1000, blank=True, default='')

    class Meta:
        db_table = 'scheduled_task_group_module'
        ordering = ['module__sort', 'module_id']
        constraints = [
            models.UniqueConstraint(
                fields=['task_group', 'module'],
                name='scheduled_task_group_module_unique',
            ),
        ]


class TasksDetails(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    type = models.SmallIntegerField(verbose_name="任务类型", default=0)
    task = models.ForeignKey(to='Tasks', to_field="id", on_delete=models.PROTECT)
    ui_case = models.ForeignKey(to='auto_ui.UiCase', to_field="id", on_delete=models.SET_NULL, null=True)
    api_case = models.ForeignKey(to='auto_api.ApiCase', to_field="id", on_delete=models.SET_NULL, null=True)
    api_case_revision = models.ForeignKey(
        to='auto_api.ApiCaseRevision',
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    api_case_release = models.ForeignKey(
        to='auto_api.ApiCaseRelease',
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    version_policy = models.CharField(
        verbose_name="版本策略",
        max_length=16,
        choices=TaskCaseVersionPolicyEnum.choices(),
        default=TaskCaseVersionPolicyEnum.PINNED.value,
    )
    bound_checksum = models.CharField(verbose_name="绑定配置哈希", max_length=64, null=True, blank=True)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="更新人",
        related_name="tasks_details_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    bound_at = models.DateTimeField(verbose_name="版本绑定时间", null=True, blank=True)
    pytest_case = models.ForeignKey(to='auto_pytest.PytestCase', to_field="id", on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'tasks_details'
        ordering = ['-id']
