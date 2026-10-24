# -*- coding: utf-8 -*-
from datetime import timedelta

from django.utils import timezone

from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentArtifact, AiAgentDefinition, AiAgentEvent, AiAgentToolCall


class AgentBudgetService:
    @staticmethod
    def policy(task) -> dict:
        if not task or not task.agent_key:
            return {}
        definition = AiAgentDefinition.objects.filter(
            agent_key=task.agent_key,
            version=task.agent_version,
        ).first()
        return dict(definition.budget_policy or {}) if definition else {}

    @classmethod
    def check_deadline(cls, task):
        policy = cls.policy(task)
        deadline_seconds = int(policy.get("deadline_seconds") or 0)
        if deadline_seconds and timezone.now() > task.create_time + timedelta(seconds=deadline_seconds):
            raise ai_service_error(f"Agent 任务已超过总截止时间 {deadline_seconds} 秒")

    @classmethod
    def before_model_call(cls, task):
        if not task:
            return
        cls.check_deadline(task)
        limit = int(cls.policy(task).get("max_model_calls") or 0)
        used = AiAgentEvent.objects.filter(task=task, event_type="model_call_started").count()
        if limit and used >= limit:
            raise ai_service_error(f"Agent 模型调用次数已达到上限 {limit}")

    @classmethod
    def after_model_call(cls, task):
        if not task:
            return
        limit = int(cls.policy(task).get("max_total_tokens") or 0)
        if not limit:
            return
        used = 0
        for data in AiAgentEvent.objects.filter(
                task=task,
                event_type="model_call_finished",
        ).values_list("data", flat=True):
            usage = (data or {}).get("usage") or {}
            used += int(usage.get("total_tokens") or usage.get("total_token_count") or 0)
        if used > limit:
            raise ai_service_error(f"Agent 模型 token 用量已超过上限 {limit}")

    @classmethod
    def before_mcp_call(cls, task):
        if not task:
            return
        cls.check_deadline(task)
        limit = int(cls.policy(task).get("max_mcp_calls") or 0)
        used = AiAgentToolCall.objects.filter(task=task).count()
        if limit and used >= limit:
            raise ai_service_error(f"Agent MCP 调用次数已达到上限 {limit}")

    @classmethod
    def before_replan(cls, task):
        if not task:
            return
        cls.check_deadline(task)
        limit = int(cls.policy(task).get("max_replans") or 0)
        used = AiAgentArtifact.objects.filter(task=task, artifact_type="replan").count()
        if limit and used >= limit:
            raise ai_service_error(f"Agent 工具链重规划次数已达到上限 {limit}")
