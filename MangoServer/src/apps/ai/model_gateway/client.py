# -*- coding: utf-8 -*-
import time
from django.utils import timezone

from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentTaskStep
from src.apps.ai.services.agent.budget import AgentBudgetService
from src.apps.ai.services.harness.artifact import AgentEventService
from src.apps.system.services.ai.client import AiService


class AgentModelGateway:
    @classmethod
    def json_chat(cls, *, task=None, **kwargs):
        if not task:
            return AiService.json_chat(**kwargs)
        chunk_state = {"count": 0, "last_event_at": 0.0}

        def on_chunk(_chunk):
            chunk_state["count"] += 1
            now = time.monotonic()
            AiAgentTask.objects.filter(id=task.id).update(heartbeat_at=timezone.now())
            AiAgentTaskStep.objects.filter(
                task_id=task.id,
                status=AiAgentTaskStatusEnum.RUNNING.value,
            ).update(heartbeat_at=timezone.now())
            if now - chunk_state["last_event_at"] >= 2:
                AgentEventService.emit(
                    task,
                    "model_stream_progress",
                    f"正在接收模型分片 {chunk_state['count']}",
                    data={"chunk_count": chunk_state["count"]},
                )
                chunk_state["last_event_at"] = now

        return cls._call(
            "json_chat",
            task,
            lambda: AiService.stream_json_chat(on_chunk=on_chunk, **kwargs),
        )

    @classmethod
    def chat_with_tools(cls, *, task=None, **kwargs):
        return cls._call("chat_with_tools", task, lambda: AiService.chat_with_tools(**kwargs))

    @classmethod
    def _call(cls, operation: str, task, callback):
        if not task:
            return callback()
        AgentBudgetService.before_model_call(task)
        started = time.monotonic()
        AgentEventService.emit(task, "model_call_started", operation, data={"operation": operation})
        AiAgentTask.objects.filter(
            id=task.id,
            status__in=[AiAgentTaskStatusEnum.CLAIMED.value, AiAgentTaskStatusEnum.RUNNING.value],
        ).update(status=AiAgentTaskStatusEnum.WAITING_MODEL.value, heartbeat_at=timezone.now())
        try:
            response = callback()
            choices = response.get("choices") if isinstance(response, dict) else []
            finish_reason = (choices or [{}])[0].get("finish_reason") if choices else None
            if finish_reason == "length":
                raise ai_service_error("模型输出因 token 上限被截断，本次结构化结果不完整")
            if finish_reason == "content_filter":
                raise ai_service_error("模型输出被内容策略中止，本次结果不完整")
            usage = response.get("usage") if isinstance(response, dict) else {}
            AgentEventService.emit(
                task,
                "model_call_finished",
                operation,
                data={
                    "operation": operation,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "usage": usage or {},
                },
            )
            AgentBudgetService.after_model_call(task)
            return response
        except Exception as exc:
            AgentEventService.emit(
                task,
                "model_call_failed",
                str(exc),
                data={
                    "operation": operation,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                },
            )
            raise
        finally:
            AiAgentTask.objects.filter(
                id=task.id,
                status=AiAgentTaskStatusEnum.WAITING_MODEL.value,
            ).update(status=AiAgentTaskStatusEnum.RUNNING.value, heartbeat_at=timezone.now())
