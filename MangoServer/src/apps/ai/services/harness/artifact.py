# -*- coding: utf-8 -*-
import hashlib
import json

from src.apps.ai.models import AiAgentArtifact, AiAgentEvaluation, AiAgentEvent
from src.apps.ai.services.core import mask_sensitive


class AgentArtifactService:
    @staticmethod
    def create(task, artifact_type: str, content: dict | list | None = None, *, step=None, task_item=None,
               status="validated"):
        safe_content = mask_sensitive(content or {})
        raw = json.dumps(safe_content, ensure_ascii=False, sort_keys=True, default=str)
        artifact = AiAgentArtifact.objects.create(
            task=task,
            step=step,
            task_item=task_item,
            artifact_type=artifact_type,
            content_json=safe_content if isinstance(safe_content, dict) else {"items": safe_content},
            content_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            status=status,
        )
        if step:
            step.checkpoint_artifact = artifact
            step.save(update_fields=["checkpoint_artifact", "update_time"])
        return artifact

    @staticmethod
    def checkpoint(task, step_key: str):
        artifact = (
            AiAgentArtifact.objects.filter(
                task=task,
                step__step_key=step_key,
                status__in=["validated", "committed"],
            )
            .order_by("-id")
            .first()
        )
        return artifact.content_json if artifact else None

    @staticmethod
    def evaluate(task, evaluator_key: str, passed: bool, *, score=100, metrics=None, findings=None, task_item=None):
        return AiAgentEvaluation.objects.create(
            task=task,
            task_item=task_item,
            evaluator_key=evaluator_key,
            score=score,
            passed=passed,
            metrics=metrics or {},
            findings=findings or [],
        )


class AgentEventService:
    @staticmethod
    def emit(task, event_type: str, message: str = "", data=None, *, step_key=None, task_item=None):
        return AiAgentEvent.objects.create(
            task=task,
            event_type=event_type,
            step_key=step_key,
            task_item=task_item,
            message=(message or "")[:512],
            data=mask_sensitive(data or {}),
        )
