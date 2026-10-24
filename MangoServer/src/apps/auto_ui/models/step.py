from django.db import models

from src.apps.auto_ui.exceptions import (
    AUTO_UI_STEP_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    AUTO_UI_STEP_CASE_STEP_RELATION_DELETE_BINDING_INVALID,
    AutoUiError,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from django.apps import apps


class PageSteps(models.Model):
    """页面步骤表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    page = models.ForeignKey(to="Page", to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="page_steps_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="步骤名称", max_length=64)
    run_flow = models.TextField(verbose_name="步骤顺序", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)
    flow_data = models.JSONField(verbose_name="flow_data", default=dict, blank=True)
    goal = models.TextField(verbose_name="步骤目标", null=True, blank=True)
    entry_criteria = models.JSONField(verbose_name="进入条件", default=dict, blank=True)
    success_criteria = models.JSONField(verbose_name="成功条件", default=dict, blank=True)
    healing_enabled = models.BooleanField(verbose_name="启用步骤自愈", default=False)
    healing_policy = models.JSONField(verbose_name="步骤自愈策略", default=dict, blank=True)
    config_version = models.PositiveBigIntegerField(verbose_name="步骤配置版本", default=1)

    class Meta:
        db_table = 'page_steps'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if PageStepsDetailed.objects.filter(page_step=self).exists():
            raise AutoUiError(AUTO_UI_STEP_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        if apps.get_model("auto_ui", "UiCaseStepsDetailed").objects.filter(page_step=self).exists():
            raise AutoUiError(AUTO_UI_STEP_CASE_STEP_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class PageStepsDetailed(models.Model):
    """步骤详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page_step = models.ForeignKey(to="PageSteps", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="page_steps_detailed_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    # type==0是进行操作，==1是进行断言
    type = models.SmallIntegerField(verbose_name="操作类型")
    ele_name = models.ForeignKey(to="PageElement", to_field="id", on_delete=models.SET_NULL, null=True)
    step_sort = models.IntegerField(verbose_name="顺序的排序")
    # 操作和断言
    ope_key = models.CharField(verbose_name="对该元素的操作类型", max_length=1048, null=True, blank=True)
    ope_value = models.JSONField(verbose_name="对该元素的操作类型", null=True, blank=True)
    # sql
    sql_execute = models.JSONField(verbose_name="sql步骤", null=True, blank=True)
    key_list = models.JSONField(verbose_name="sql查询结果的key_list", null=True, blank=True)
    sql = models.CharField(verbose_name="sql", max_length=1048, null=True, blank=True)
    # 自定义
    custom = models.JSONField(verbose_name="自定义缓存步骤", null=True, blank=True)
    key = models.CharField(verbose_name="key", max_length=1048, null=True, blank=True)
    value = models.CharField(verbose_name="value", max_length=1048, null=True, blank=True)
    # 条件
    condition_value = models.JSONField(verbose_name="条件判断", null=True, blank=True)
    # func
    func = models.TextField(verbose_name="func", null=True, blank=True)
    precondition = models.JSONField(verbose_name="节点前置条件", default=dict, blank=True)
    postcondition = models.JSONField(verbose_name="节点后置条件", default=dict, blank=True)

    class Meta:
        db_table = 'page_steps_detailed'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class UiPageStepStateBaseline(models.Model):
    """页面步骤检查点状态基线。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page_step = models.ForeignKey(
        to="PageSteps",
        to_field="id",
        related_name="state_baselines",
        on_delete=models.CASCADE,
    )
    checkpoint_key = models.CharField(verbose_name="检查点Key", max_length=128)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    config_version = models.PositiveBigIntegerField(verbose_name="步骤配置版本")
    state_signature = models.JSONField(verbose_name="脱敏状态签名", default=dict, blank=True)
    status = models.CharField(verbose_name="基线状态", max_length=24, default="candidate", db_index=True)
    success_count = models.PositiveIntegerField(verbose_name="成功次数", default=1)
    last_seen_at = models.DateTimeField(verbose_name="最近命中时间", auto_now=True)

    class Meta:
        db_table = 'ui_page_step_state_baseline'
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=['page_step', 'checkpoint_key', 'test_env', 'config_version'],
                name='ui_step_baseline_checkpoint_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['page_step', 'test_env', 'status']),
            models.Index(fields=['checkpoint_key', 'status']),
        ]


class UiPageStepHealRecord(models.Model):
    """页面步骤AI自愈修复记录。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page_step = models.ForeignKey(
        to="PageSteps",
        to_field="id",
        related_name="heal_records",
        on_delete=models.CASCADE,
    )
    executor_task = models.ForeignKey(
        to='task_center.ExecutorTask',
        to_field='id',
        related_name='ui_page_step_heal_records',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    trace_id = models.UUIDField(verbose_name="链路ID", unique=True)
    dispatch_id = models.CharField(verbose_name="派发ID", max_length=128, null=True, blank=True, db_index=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True)
    source_version = models.PositiveBigIntegerField(verbose_name="运行时配置版本")
    failed_node_id = models.CharField(verbose_name="失败节点ID", max_length=128, null=True, blank=True)
    trigger = models.CharField(verbose_name="触发原因", max_length=128)
    before_state = models.JSONField(verbose_name="修复前状态", default=dict, blank=True)
    after_state = models.JSONField(verbose_name="修复后状态", default=dict, blank=True)
    proposed_plan = models.JSONField(verbose_name="建议补丁", default=dict, blank=True)
    executed_plan = models.JSONField(verbose_name="实际执行补丁", default=dict, blank=True)
    status = models.CharField(verbose_name="修复状态", max_length=24, db_index=True)
    writeback_status = models.CharField(verbose_name="回写状态", max_length=24, default="none", db_index=True)
    confidence = models.FloatField(verbose_name="置信度", default=0)
    user_message = models.CharField(verbose_name="用户提示", max_length=500, blank=True, default='')
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="reviewed_ui_page_step_heals",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(verbose_name="审核时间", null=True, blank=True)

    class Meta:
        db_table = 'ui_page_step_heal_record'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['page_step', 'status', 'create_time']),
            models.Index(fields=['page_step', 'writeback_status']),
            models.Index(fields=['executor_task', 'status']),
        ]


class UiPageStepVersion(models.Model):
    """页面步骤正式配置版本。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    page_step = models.ForeignKey(
        to="PageSteps",
        to_field="id",
        related_name="versions",
        on_delete=models.CASCADE,
    )
    version = models.PositiveBigIntegerField(verbose_name="版本号")
    config_snapshot = models.JSONField(verbose_name="配置快照", default=dict, blank=True)
    source = models.CharField(verbose_name="版本来源", max_length=32, default="manual")
    source_heal_record = models.ForeignKey(
        to="UiPageStepHealRecord",
        to_field="id",
        related_name="created_versions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="created_ui_page_step_versions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'ui_page_step_version'
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['page_step', 'version'],
                name='ui_page_step_version_unique',
            ),
        ]
        indexes = [models.Index(fields=['page_step', 'version'])]
