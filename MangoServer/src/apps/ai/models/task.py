# -*- coding: utf-8 -*-
from django.db import models

from src.apps.ai.enums import (
    AiAgentTaskStatusEnum,
    AiAgentToolCallStatusEnum,
    AiAgentTaskTypeEnum,
    AiMcpToolRiskLevelEnum,
)
from src.apps.user.models import User


class AiAgentTask(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task_no = models.CharField(verbose_name="任务编号", max_length=64, unique=True)
    task_type = models.SmallIntegerField(verbose_name="任务类型", choices=AiAgentTaskTypeEnum.choices(), db_index=True)
    title = models.CharField(verbose_name="任务标题", max_length=256)
    status = models.SmallIntegerField(
        verbose_name="任务状态",
        choices=AiAgentTaskStatusEnum.choices(),
        default=AiAgentTaskStatusEnum.PENDING.value,
        db_index=True,
    )
    skill = models.ForeignKey(to="AiSkill", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    model_name = models.CharField(verbose_name="模型名称", max_length=128, null=True, blank=True)
    input_data = models.JSONField(verbose_name="输入数据", default=dict, blank=True)
    output_data = models.JSONField(verbose_name="输出数据", default=dict, blank=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    agent_key = models.CharField(verbose_name="Agent编码", max_length=64, null=True, blank=True, db_index=True)
    agent_version = models.PositiveIntegerField(verbose_name="Agent版本", null=True, blank=True)
    current_step_key = models.CharField(verbose_name="当前阶段", max_length=64, null=True, blank=True)
    attempt_no = models.PositiveIntegerField(verbose_name="尝试次数", default=0)
    worker_id = models.CharField(verbose_name="Worker编码", max_length=128, null=True, blank=True, db_index=True)
    lease_expires_at = models.DateTimeField(verbose_name="租约到期时间", null=True, blank=True, db_index=True)
    heartbeat_at = models.DateTimeField(verbose_name="心跳时间", null=True, blank=True)
    cancel_requested = models.BooleanField(verbose_name="请求取消", default=False)
    input_snapshot = models.JSONField(verbose_name="输入快照", default=dict, blank=True)
    result_summary = models.JSONField(verbose_name="结果摘要", default=dict, blank=True)
    model_snapshot = models.JSONField(verbose_name="模型快照", default=dict, blank=True)
    mcp_snapshot = models.JSONField(verbose_name="MCP能力快照", default=dict, blank=True)
    context_hash = models.CharField(verbose_name="上下文Hash", max_length=64, null=True, blank=True, db_index=True)
    skill_version = models.ForeignKey(to="AiSkillVersion", to_field="id", null=True, blank=True,
                                      on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_agent_task"
        ordering = ["-id"]


class AiAgentTaskStep(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    step_key = models.CharField(verbose_name="阶段编码", max_length=64, db_index=True)
    step_name = models.CharField(verbose_name="阶段名称", max_length=128)
    step_order = models.IntegerField(verbose_name="阶段顺序", default=0)
    status = models.SmallIntegerField(
        verbose_name="阶段状态",
        choices=AiAgentTaskStatusEnum.choices(),
        default=AiAgentTaskStatusEnum.PENDING.value,
        db_index=True,
    )
    progress = models.IntegerField(verbose_name="阶段进度", default=0)
    input_data = models.JSONField(verbose_name="阶段输入", default=dict, blank=True)
    output_data = models.JSONField(verbose_name="阶段输出", default=dict, blank=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    retry_count = models.IntegerField(verbose_name="重试次数", default=0)
    start_time = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)
    step_version = models.PositiveIntegerField(verbose_name="阶段版本", default=1)
    checkpoint_artifact = models.ForeignKey(
        to="AiAgentArtifact",
        to_field="id",
        null=True,
        blank=True,
        related_name="checkpoint_steps",
        on_delete=models.SET_NULL,
    )
    attempt_no = models.PositiveIntegerField(verbose_name="尝试次数", default=0)
    heartbeat_at = models.DateTimeField(verbose_name="心跳时间", null=True, blank=True)
    error_category = models.CharField(verbose_name="错误分类", max_length=32, null=True, blank=True)

    class Meta:
        db_table = "ai_agent_task_step"
        ordering = ["task_id", "step_order", "id"]
        indexes = [
            models.Index(fields=["task", "step_order"]),
            models.Index(fields=["task", "status"]),
        ]


class AiAgentToolCall(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    step_no = models.IntegerField(verbose_name="步骤序号", default=1)
    server = models.ForeignKey(to="AiMcpServer", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    tool_name = models.CharField(verbose_name="工具名称", max_length=256)
    arguments = models.JSONField(verbose_name="调用参数", default=dict, blank=True)
    result = models.JSONField(verbose_name="调用结果", default=dict, blank=True)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=AiAgentToolCallStatusEnum.choices(),
        default=AiAgentToolCallStatusEnum.SUCCESS.value,
    )
    risk_level = models.SmallIntegerField(
        verbose_name="风险等级",
        choices=AiMcpToolRiskLevelEnum.choices(),
        default=AiMcpToolRiskLevelEnum.READ.value,
    )
    confirm_required = models.BooleanField(verbose_name="是否需要确认", default=False)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    start_time = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)
    task_item = models.ForeignKey(to="AiAgentTaskItem", null=True, blank=True, on_delete=models.SET_NULL)
    stage_key = models.CharField(verbose_name="阶段编码", max_length=64, null=True, blank=True, db_index=True)
    idempotency_key = models.CharField(verbose_name="幂等键", max_length=128, null=True, blank=True, db_index=True)
    request_hash = models.CharField(verbose_name="请求Hash", max_length=64, null=True, blank=True)
    result_hash = models.CharField(verbose_name="结果Hash", max_length=64, null=True, blank=True)
    mcp_tool_schema_hash = models.CharField(verbose_name="工具Schema Hash", max_length=64, null=True, blank=True)
    duration_ms = models.PositiveIntegerField(verbose_name="耗时毫秒", null=True, blank=True)
    external_asset_ids = models.JSONField(verbose_name="外部资产ID", default=dict, blank=True)

    class Meta:
        db_table = "ai_agent_tool_call"
        ordering = ["task_id", "step_no", "id"]


class AiAgentTaskItem(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    manual_case_id = models.IntegerField(verbose_name="功能用例ID", db_index=True)
    item_order = models.PositiveIntegerField(verbose_name="子项顺序", default=0)
    status = models.SmallIntegerField(verbose_name="状态", choices=AiAgentTaskStatusEnum.choices(),
                                      default=AiAgentTaskStatusEnum.PENDING.value, db_index=True)
    attempt_no = models.PositiveIntegerField(verbose_name="尝试次数", default=0)
    current_step_key = models.CharField(verbose_name="当前阶段", max_length=64, null=True, blank=True)
    checkpoint = models.JSONField(verbose_name="检查点", default=dict, blank=True)
    api_case_id = models.IntegerField(verbose_name="API用例ID", null=True, blank=True)
    execution_record_id = models.IntegerField(verbose_name="执行记录ID", null=True, blank=True)
    result_summary = models.JSONField(verbose_name="结果摘要", default=dict, blank=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)

    class Meta:
        db_table = "ai_agent_task_item"
        ordering = ["task_id", "item_order", "id"]
        unique_together = ("task", "manual_case_id")
