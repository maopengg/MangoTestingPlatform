# -*- coding: utf-8 -*-
from django.db import models

from src.apps.user.models import User


class AiAssistantSession(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    title = models.CharField(verbose_name="会话标题", max_length=128, default="新会话")
    current_page = models.CharField(verbose_name="当前页面", max_length=512, null=True, blank=True)
    page_context = models.JSONField(verbose_name="页面上下文", default=dict, blank=True)
    status = models.CharField(verbose_name="状态", max_length=32, default="active", db_index=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_assistant_session"
        ordering = ["-id"]


class AiAssistantMessage(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    session = models.ForeignKey(to="AiAssistantSession", to_field="id", on_delete=models.CASCADE)
    role = models.CharField(verbose_name="消息角色", max_length=32)
    content = models.TextField(verbose_name="消息内容", null=True, blank=True)
    tool_name = models.CharField(verbose_name="工具名称", max_length=256, null=True, blank=True)
    tool_arguments = models.JSONField(verbose_name="工具参数", default=dict, blank=True)
    tool_result = models.JSONField(verbose_name="工具结果", default=dict, blank=True)
    metadata = models.JSONField(verbose_name="元数据", default=dict, blank=True)

    class Meta:
        db_table = "ai_assistant_message"
        ordering = ["id"]
