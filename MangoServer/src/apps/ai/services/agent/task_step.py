# -*- coding: utf-8 -*-
from django.utils import timezone

from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentTaskStep
from src.apps.ai.services.core import AiTaskService, mask_sensitive
from src.apps.ai.services.harness.artifact import AgentArtifactService, AgentEventService


class AiAgentTaskStepService:
    @staticmethod
    def create_steps(task: AiAgentTask, step_defs: list[dict]) -> list[AiAgentTaskStep]:
        existing = set(AiAgentTaskStep.objects.filter(task=task).values_list("step_key", flat=True))
        steps = []
        for index, step_def in enumerate(step_defs, start=1):
            step_key = step_def["key"]
            if step_key in existing:
                continue
            steps.append(
                AiAgentTaskStep.objects.create(
                    task=task,
                    step_key=step_key,
                    step_name=step_def.get("name") or step_key,
                    step_order=step_def.get("order") or index,
                    status=AiAgentTaskStatusEnum.PENDING.value,
                    progress=0,
                    input_data=mask_sensitive(step_def.get("input_data") or {}),
                    output_data={},
                )
            )
        return steps

    @classmethod
    def reset_steps(cls, task: AiAgentTask, step_defs: list[dict]):
        AiAgentTaskStep.objects.filter(task=task).delete()
        return cls.create_steps(task, step_defs)

    @classmethod
    def reset_from_step(
            cls,
            task: AiAgentTask,
            step_defs: list[dict],
            step_key: str | None = None,
    ):
        cls.create_steps(task, step_defs)
        steps = list(cls.list_steps(task))
        start_order = None
        if step_key:
            start_order = next(
                (step.step_order for step in steps if step.step_key == step_key),
                None,
            )
        if start_order is None:
            start_order = next(
                (
                    step.step_order
                    for step in steps
                    if step.status != AiAgentTaskStatusEnum.SUCCESS.value
                ),
                steps[-1].step_order if steps else 1,
            )
        AiAgentTaskStep.objects.filter(task=task, step_order__gte=start_order).update(
            status=AiAgentTaskStatusEnum.PENDING.value,
            progress=0,
            output_data={},
            error_message=None,
            error_category=None,
            start_time=None,
            end_time=None,
            checkpoint_artifact=None,
            heartbeat_at=None,
        )
        task.current_step_key = None
        task.save(update_fields=["current_step_key", "update_time"])
        return cls.list_steps(task)

    @staticmethod
    def list_steps(task: AiAgentTask):
        return AiAgentTaskStep.objects.filter(task=task).order_by("step_order", "id")

    @staticmethod
    def get_step(task: AiAgentTask, step_key: str) -> AiAgentTaskStep:
        return AiAgentTaskStep.objects.get(task=task, step_key=step_key)

    @classmethod
    def start_step(cls, task: AiAgentTask, step_key: str, input_data: dict | None = None) -> AiAgentTaskStep:
        task.refresh_from_db(fields=["cancel_requested", "status"])
        if task.cancel_requested:
            task.status = AiAgentTaskStatusEnum.CANCELLED.value
            task.save(update_fields=["status", "update_time"])
            raise ai_service_error("任务已取消")
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.RUNNING.value
        step.attempt_no += 1
        step.heartbeat_at = timezone.now()
        step.progress = max(step.progress, 1)
        step.error_message = None
        step.start_time = step.start_time or timezone.now()
        if input_data is not None:
            step.input_data = mask_sensitive(input_data)
        step.save(update_fields=["status", "progress", "error_message", "start_time", "input_data", "attempt_no",
                                 "heartbeat_at", "update_time"])
        task.current_step_key = step_key
        task.heartbeat_at = timezone.now()
        AiAgentTask.objects.filter(id=task.id).update(
            current_step_key=step_key,
            heartbeat_at=task.heartbeat_at,
        )
        AgentEventService.emit(task, "step_started", step.step_name, step_key=step_key)
        cls.update_task_progress(task, step)
        return step

    @classmethod
    def update_step(
            cls,
            task: AiAgentTask,
            step_key: str,
            progress: int,
            output_data: dict | None = None,
            detail: str = "",
    ) -> AiAgentTaskStep:
        step = cls.get_step(task, step_key)
        step.progress = max(0, min(100, int(progress)))
        if output_data is not None:
            current_output = dict(step.output_data or {})
            current_output.update(mask_sensitive(output_data))
            step.output_data = current_output
        step.save(update_fields=["progress", "output_data", "update_time"])
        cls.update_task_progress(task, step, detail)
        return step

    @classmethod
    def finish_step(
            cls,
            task: AiAgentTask,
            step_key: str,
            output_data: dict | None = None,
            *,
            checkpoint_data: dict | list | None = None,
            artifact_status: str = "validated",
    ) -> AiAgentTaskStep:
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.SUCCESS.value
        step.progress = 100
        step.end_time = timezone.now()
        if output_data is not None:
            step.output_data = mask_sensitive(output_data)
        step.save(update_fields=["status", "progress", "end_time", "output_data", "update_time"])
        AgentArtifactService.create(
            task,
            step_key,
            checkpoint_data if checkpoint_data is not None else step.output_data,
            step=step,
            status=artifact_status,
        )
        AgentEventService.emit(task, "step_finished", step.step_name, step.output_data, step_key=step_key)
        cls.update_task_progress(task, step)
        return step

    @classmethod
    def load_checkpoint(cls, task: AiAgentTask, step_key: str):
        step = cls.get_step(task, step_key)
        if step.status != AiAgentTaskStatusEnum.SUCCESS.value:
            return None
        artifact = step.checkpoint_artifact
        if not artifact or artifact.status not in ("validated", "committed"):
            return None
        AgentEventService.emit(task, "step_resumed", f"从检查点恢复：{step.step_name}", step_key=step_key)
        return artifact.content_json

    @classmethod
    def fail_step(cls, task: AiAgentTask, step_key: str, error) -> AiAgentTaskStep:
        error_message = str(error)
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.FAIL.value
        step.error_message = error_message[:1000]
        step.error_category = cls.classify_error(error)
        step.end_time = timezone.now()
        step.save(update_fields=["status", "error_message", "error_category", "end_time", "update_time"])
        AgentEventService.emit(task, "step_failed", error_message, step_key=step_key)
        cls.update_task_progress(task, step, error_message[:300])
        return step

    @staticmethod
    def classify_error(error) -> str:
        message = str(error).lower()
        error_name = error.__class__.__name__.lower() if isinstance(error, BaseException) else ""
        if any(key in message for key in ("timeout", "timed out", "response ended", "ai请求", "模型")):
            return "model_error"
        if any(key in error_name for key in ("timeout", "connection", "request")):
            return "model_error"
        if any(key in message for key in ("json", "schema", "枚举", "校验", "断言", "覆盖门禁", "必填")):
            return "validation_error"
        if any(key in message for key in ("请选择", "不存在", "未配置", "无权限", "参数")):
            return "input_error"
        if isinstance(error, ValueError):
            return "business_error"
        return "runtime_error"

    @staticmethod
    def latest_failed_step(task: AiAgentTask) -> AiAgentTaskStep | None:
        return (
            AiAgentTaskStep.objects.filter(task=task, status=AiAgentTaskStatusEnum.FAIL.value)
            .order_by("step_order", "id")
            .first()
        )

    @staticmethod
    def aggregate_progress(task: AiAgentTask) -> int:
        steps = list(AiAgentTaskStep.objects.filter(task=task))
        if not steps:
            progress = (task.output_data or {}).get("progress") or {}
            return int(progress.get("percent") or 0)
        total = sum(max(0, min(100, int(step.progress or 0))) for step in steps)
        return round(total / len(steps))

    @classmethod
    def update_task_progress(cls, task: AiAgentTask, step: AiAgentTaskStep, detail: str = ""):
        percent = cls.aggregate_progress(task)
        AiTaskService.update_progress(
            task,
            percent,
            step.step_name,
            detail or step.error_message or "",
            {
                "step_key": step.step_key,
                "step_id": step.id,
                "step_progress": step.progress,
            },
        )
