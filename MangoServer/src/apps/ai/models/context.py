# -*- coding: utf-8 -*-
from django.db import models

from src.apps.user.models import User


class AiAgentContext(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    suite_id = models.IntegerField(verbose_name="功能测试需求ID", db_index=True)
    manual_case_id = models.IntegerField(verbose_name="功能测试用例ID", null=True, blank=True, db_index=True)
    context_type = models.CharField(verbose_name="上下文类型", max_length=64, db_index=True)
    context_hash = models.CharField(verbose_name="上下文Hash", max_length=64, db_index=True)
    source_snapshot = models.JSONField(verbose_name="输入上下文快照", default=dict, blank=True)
    result_snapshot = models.JSONField(verbose_name="输出结果快照", default=dict, blank=True)
    summary = models.TextField(verbose_name="结果摘要", null=True, blank=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    skill_snapshot = models.JSONField(verbose_name="技能快照", default=dict, blank=True)
    mcp_snapshot = models.JSONField(verbose_name="MCP快照", default=dict, blank=True)
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
