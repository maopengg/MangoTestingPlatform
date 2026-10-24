# -*- coding: utf-8 -*-
from django.db import models

from src.apps.ai.enums import (
    AiSkillStatusEnum,
)
from src.apps.user.models import User


class AiAgentDefinition(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    agent_key = models.CharField(verbose_name="Agent编码", max_length=64, db_index=True)
    version = models.PositiveIntegerField(verbose_name="版本", default=1)
    role_key = models.CharField(verbose_name="默认角色", max_length=64)
    allowed_roles = models.JSONField(verbose_name="允许角色", default=list, blank=True)
    workflow_schema = models.JSONField(verbose_name="工作流定义", default=dict, blank=True)
    prompt_template = models.TextField(verbose_name="系统提示词")
    validation_policy = models.JSONField(verbose_name="校验策略", default=dict, blank=True)
    budget_policy = models.JSONField(verbose_name="运行预算", default=dict, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1, db_index=True)

    class Meta:
        db_table = "ai_agent_definition"
        ordering = ["agent_key", "-version"]
        unique_together = ("agent_key", "version")


class AiSkillVersion(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    skill = models.ForeignKey(to="AiSkill", to_field="id", on_delete=models.CASCADE)
    version = models.PositiveIntegerField(verbose_name="版本")
    content = models.TextField(verbose_name="不可变技能内容")
    content_hash = models.CharField(verbose_name="内容Hash", max_length=64, db_index=True)
    compiled_contract = models.JSONField(verbose_name="编译协议", default=dict, blank=True)
    create_user = models.ForeignKey(to=User, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "ai_skill_version"
        ordering = ["skill_id", "-version"]
        unique_together = ("skill", "version")


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
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="ai_skill_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "ai_skill"
        ordering = ["-id"]
