# -*- coding: utf-8 -*-
from django.db import models


class AiAgentArtifact(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    step = models.ForeignKey(to="AiAgentTaskStep", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    task_item = models.ForeignKey(to="AiAgentTaskItem", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    artifact_type = models.CharField(verbose_name="产物类型", max_length=64, db_index=True)
    schema_version = models.PositiveIntegerField(verbose_name="Schema版本", default=1)
    content_json = models.JSONField(verbose_name="JSON内容", default=dict, blank=True)
    content_text = models.TextField(verbose_name="文本内容", null=True, blank=True)
    content_hash = models.CharField(verbose_name="内容Hash", max_length=64, db_index=True)
    parent_artifact = models.ForeignKey(to="self", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(verbose_name="产物状态", max_length=16, default="candidate", db_index=True)

    class Meta:
        db_table = "ai_agent_artifact"
        ordering = ["task_id", "id"]


class AiAgentEvaluation(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    task_item = models.ForeignKey(to="AiAgentTaskItem", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    evaluator_key = models.CharField(verbose_name="评估器", max_length=64, db_index=True)
    evaluator_version = models.PositiveIntegerField(verbose_name="评估器版本", default=1)
    score = models.DecimalField(verbose_name="分数", max_digits=6, decimal_places=2, default=0)
    passed = models.BooleanField(verbose_name="是否通过", default=False, db_index=True)
    metrics = models.JSONField(verbose_name="指标", default=dict, blank=True)
    findings = models.JSONField(verbose_name="发现", default=list, blank=True)

    class Meta:
        db_table = "ai_agent_evaluation"
        ordering = ["task_id", "id"]


class AiAgentEvent(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    task = models.ForeignKey(to="AiAgentTask", to_field="id", on_delete=models.CASCADE)
    event_type = models.CharField(verbose_name="事件类型", max_length=64, db_index=True)
    step_key = models.CharField(verbose_name="阶段编码", max_length=64, null=True, blank=True)
    task_item = models.ForeignKey(to="AiAgentTaskItem", to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    message = models.CharField(verbose_name="事件摘要", max_length=512, null=True, blank=True)
    data = models.JSONField(verbose_name="事件数据", default=dict, blank=True)

    class Meta:
        db_table = "ai_agent_event"
        ordering = ["task_id", "id"]
        indexes = [models.Index(fields=["task", "id"])]
