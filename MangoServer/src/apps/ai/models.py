# -*- coding: utf-8 -*-
from django.db import models

from src.apps.user.models import User
from src.common.enums.ai_enum import (
    AiAgentTaskStatusEnum,
    AiAgentToolCallStatusEnum,
    AiAgentTaskTypeEnum,
    AiMcpAuthTypeEnum,
    AiMcpStatusEnum,
    AiMcpToolRiskLevelEnum,
    AiMcpTransportTypeEnum,
    AiSkillStatusEnum,
)


class AiSkill(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="Skill名称", max_length=128)
    description = models.CharField(verbose_name="描述", max_length=512, null=True, blank=True)
    content = models.TextField(verbose_name="Skill内容")
    is_builtin = models.BooleanField(verbose_name="是否内置", default=False, db_index=True)
    skill_type = models.SmallIntegerField(verbose_name="Skill类型", default=0, db_index=True)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=AiSkillStatusEnum.choices(),
        default=AiSkillStatusEnum.PUBLISHED.value,
        db_index=True,
    )
    user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_skill_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "ai_skill"
        ordering = ["-id"]


class AiMcpServer(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="MCP服务名称", max_length=128)
    server_url = models.CharField(verbose_name="服务地址", max_length=1024)
    transport_type = models.SmallIntegerField(
        verbose_name="传输类型",
        choices=AiMcpTransportTypeEnum.choices(),
        default=AiMcpTransportTypeEnum.STREAMABLE_HTTP.value,
    )
    auth_type = models.SmallIntegerField(
        verbose_name="鉴权方式",
        choices=AiMcpAuthTypeEnum.choices(),
        default=AiMcpAuthTypeEnum.NONE.value,
    )
    auth_config = models.JSONField(verbose_name="鉴权配置", default=dict)
    description = models.CharField(verbose_name="描述", max_length=512, null=True, blank=True)
    prompt = models.TextField(verbose_name="MCP使用提示词")
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=AiMcpStatusEnum.choices(),
        default=AiMcpStatusEnum.ENABLED.value,
        db_index=True,
    )
    last_sync_time = models.DateTimeField(verbose_name="最近同步时间", null=True, blank=True)
    last_test_time = models.DateTimeField(verbose_name="最近测试时间", null=True, blank=True)
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_mcp_server_create_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_mcp_server_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "ai_mcp_server"
        ordering = ["-id"]


class AiMcpTool(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    server = models.ForeignKey(to=AiMcpServer, to_field="id", on_delete=models.CASCADE)
    name = models.CharField(verbose_name="工具名称", max_length=256, db_index=True)
    title = models.CharField(verbose_name="展示名称", max_length=256, null=True, blank=True)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    input_schema = models.JSONField(verbose_name="入参结构", default=dict)
    output_schema = models.JSONField(verbose_name="出参结构", default=dict)
    tool_type = models.CharField(verbose_name="类型", max_length=32, default="tool")
    risk_level = models.SmallIntegerField(
        verbose_name="风险等级",
        choices=AiMcpToolRiskLevelEnum.choices(),
        default=AiMcpToolRiskLevelEnum.READ.value,
        db_index=True,
    )
    write_operation = models.BooleanField(verbose_name="是否写操作", default=False)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    require_confirm = models.BooleanField(verbose_name="是否需要确认", default=False)

    class Meta:
        db_table = "ai_mcp_tool"
        ordering = ["server_id", "name"]
        unique_together = ("server", "name", "tool_type")


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
    skill = models.ForeignKey(to=AiSkill, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    model_name = models.CharField(verbose_name="模型名称", max_length=128, null=True, blank=True)
    input_data = models.JSONField(verbose_name="输入数据", default=dict)
    output_data = models.JSONField(verbose_name="输出数据", default=dict)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_agent_task"
        ordering = ["-id"]


class AiAgentTaskStep(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to=AiAgentTask, to_field="id", on_delete=models.CASCADE)
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
    input_data = models.JSONField(verbose_name="阶段输入", default=dict)
    output_data = models.JSONField(verbose_name="阶段输出", default=dict)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    retry_count = models.IntegerField(verbose_name="重试次数", default=0)
    start_time = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)

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
    task = models.ForeignKey(to=AiAgentTask, to_field="id", on_delete=models.CASCADE)
    step_no = models.IntegerField(verbose_name="步骤序号", default=1)
    server = models.ForeignKey(to=AiMcpServer, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    tool_name = models.CharField(verbose_name="工具名称", max_length=256)
    arguments = models.JSONField(verbose_name="调用参数", default=dict)
    result = models.JSONField(verbose_name="调用结果", default=dict)
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

    class Meta:
        db_table = "ai_agent_tool_call"
        ordering = ["task_id", "step_no", "id"]


class AiAgentContext(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    suite_id = models.IntegerField(verbose_name="功能测试需求ID", db_index=True)
    manual_case_id = models.IntegerField(verbose_name="功能测试用例ID", null=True, blank=True, db_index=True)
    context_type = models.CharField(verbose_name="上下文类型", max_length=64, db_index=True)
    context_hash = models.CharField(verbose_name="上下文Hash", max_length=64, db_index=True)
    source_snapshot = models.JSONField(verbose_name="输入上下文快照", default=dict)
    result_snapshot = models.JSONField(verbose_name="输出结果快照", default=dict)
    summary = models.TextField(verbose_name="结果摘要", null=True, blank=True)
    task = models.ForeignKey(to=AiAgentTask, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    skill_snapshot = models.JSONField(verbose_name="技能快照", default=dict)
    mcp_snapshot = models.JSONField(verbose_name="MCP快照", default=dict)
    user_instruction = models.TextField(verbose_name="用户补充要求", null=True, blank=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_agent_context"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["suite_id", "context_type", "context_hash"]),
            models.Index(fields=["manual_case_id", "context_type"]),
            models.Index(fields=["task"]),
        ]


class AiAssistantSession(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    title = models.CharField(verbose_name="会话标题", max_length=128, default="新会话")
    current_page = models.CharField(verbose_name="当前页面", max_length=512, null=True, blank=True)
    page_context = models.JSONField(verbose_name="页面上下文", default=dict)
    status = models.CharField(verbose_name="状态", max_length=32, default="active", db_index=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_assistant_session"
        ordering = ["-id"]


class AiAssistantMessage(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    session = models.ForeignKey(to=AiAssistantSession, to_field="id", on_delete=models.CASCADE)
    role = models.CharField(verbose_name="消息角色", max_length=32)
    content = models.TextField(verbose_name="消息内容", null=True, blank=True)
    tool_name = models.CharField(verbose_name="工具名称", max_length=256, null=True, blank=True)
    tool_arguments = models.JSONField(verbose_name="工具参数", default=dict)
    tool_result = models.JSONField(verbose_name="工具结果", default=dict)
    metadata = models.JSONField(verbose_name="元数据", default=dict)

    class Meta:
        db_table = "ai_assistant_message"
        ordering = ["id"]
