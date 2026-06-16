# -*- coding: utf-8 -*-
from django.utils import timezone

from src.apps.ai.models import AiAgentTask, AiAgentTaskStep
from src.apps.ai.service.core import AiTaskService, mask_sensitive
from src.common.enums.ai_enum import AiAgentTaskStatusEnum


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

    @staticmethod
    def list_steps(task: AiAgentTask):
        return AiAgentTaskStep.objects.filter(task=task).order_by("step_order", "id")

    @staticmethod
    def get_step(task: AiAgentTask, step_key: str) -> AiAgentTaskStep:
        return AiAgentTaskStep.objects.get(task=task, step_key=step_key)

    @classmethod
    def start_step(cls, task: AiAgentTask, step_key: str, input_data: dict | None = None) -> AiAgentTaskStep:
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.RUNNING.value
        step.progress = max(step.progress, 1)
        step.error_message = None
        step.start_time = step.start_time or timezone.now()
        if input_data is not None:
            step.input_data = mask_sensitive(input_data)
        step.save(update_fields=["status", "progress", "error_message", "start_time", "input_data", "update_time"])
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
    def finish_step(cls, task: AiAgentTask, step_key: str, output_data: dict | None = None) -> AiAgentTaskStep:
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.SUCCESS.value
        step.progress = 100
        step.end_time = timezone.now()
        if output_data is not None:
            step.output_data = mask_sensitive(output_data)
        step.save(update_fields=["status", "progress", "end_time", "output_data", "update_time"])
        cls.update_task_progress(task, step)
        return step

    @classmethod
    def fail_step(cls, task: AiAgentTask, step_key: str, error_message: str) -> AiAgentTaskStep:
        step = cls.get_step(task, step_key)
        step.status = AiAgentTaskStatusEnum.FAIL.value
        step.error_message = error_message[:1000]
        step.end_time = timezone.now()
        step.save(update_fields=["status", "error_message", "end_time", "update_time"])
        cls.update_task_progress(task, step, error_message[:300])
        return step

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
