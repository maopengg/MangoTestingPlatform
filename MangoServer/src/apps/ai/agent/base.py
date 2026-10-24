# -*- coding: utf-8 -*-
from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask
from src.apps.ai.services.agent.task_step import AiAgentTaskStepService
from src.apps.ai.services.core import AiTaskService
from src.apps.ai.services.harness.artifact import AgentEventService
from src.apps.ai.services.harness.definition import AgentDefinitionService


class BaseAgent:
    task_type: int | None = None
    agent_key: str | None = None
    step_defs: list[dict] = []

    @classmethod
    def create_task(cls, title: str, input_data: dict, user_id: int | None = None, skill=None) -> AiAgentTask:
        definition = AgentDefinitionService.active(cls.agent_key)
        task = AiTaskService.create_task(
            cls.task_type,
            title,
            input_data,
            user_id=user_id,
            skill=skill,
            definition=definition,
        )
        AiAgentTaskStepService.create_steps(task, cls.step_defs)
        return task

    @classmethod
    def dispatch(cls, task_id: int):
        task = AiAgentTask.objects.get(id=task_id)
        AgentEventService.emit(task, "task_queued", "任务已进入 Agent Worker 队列")

    @classmethod
    def execute_checkpointed_step(
            cls,
            task: AiAgentTask,
            step_key: str,
            operation,
            *,
            input_data: dict | None = None,
            summarize=None,
            artifact_status: str = "validated",
    ):
        checkpoint = AiAgentTaskStepService.load_checkpoint(task, step_key)
        if checkpoint is not None:
            return checkpoint
        AiAgentTaskStepService.start_step(task, step_key, input_data)
        result = operation()
        output = summarize(result) if summarize else result
        AiAgentTaskStepService.finish_step(
            task,
            step_key,
            output if isinstance(output, dict) else {"value": output},
            checkpoint_data=result,
            artifact_status=artifact_status,
        )
        return result

    @classmethod
    def run_safely(cls, task_id: int):
        raise ai_service_error("请使用 python manage.py run_agent_worker 执行 Agent 任务")

    @classmethod
    def run(cls, task: AiAgentTask):
        raise NotImplementedError

    @classmethod
    def status(cls, task_id: int | None = None, **filters):
        queryset = AiAgentTask.objects.filter(task_type=cls.task_type).order_by("-id")
        if task_id:
            task = queryset.get(id=task_id)
        else:
            task = cls.find_latest_task(queryset, **filters)
        if not task:
            return None
        return AiTaskService.reconcile_interrupted_task(task)

    @classmethod
    def find_latest_task(cls, queryset, **filters):
        for task in queryset[:200]:
            input_data = task.input_data or {}
            matched = True
            for key, value in filters.items():
                if value is None:
                    continue
                if str(input_data.get(key) or "") != str(value):
                    matched = False
                    break
            if matched:
                return task
        return None

    @classmethod
    def steps(cls, task_id: int):
        task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
        return AiAgentTaskStepService.list_steps(task)

    @classmethod
    def retry(cls, task_id: int, input_patch: dict | None = None):
        task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
        if task.status in [
            AiAgentTaskStatusEnum.PENDING.value,
            AiAgentTaskStatusEnum.CLAIMED.value,
            AiAgentTaskStatusEnum.RUNNING.value,
            AiAgentTaskStatusEnum.WAITING_MODEL.value,
        ]:
            raise ai_service_error("当前任务正在运行中，请等待完成后再操作")
        if input_patch:
            input_data = dict(task.input_data or {})
            input_data.update(input_patch)
            task.input_data = input_data
        task.status = AiAgentTaskStatusEnum.PENDING.value
        task.error_message = None
        task.output_data = {}
        task.worker_id = None
        task.lease_expires_at = None
        task.cancel_requested = False
        task.save(
            update_fields=["status", "error_message", "output_data", "input_data", "worker_id", "lease_expires_at",
                           "cancel_requested", "update_time"])
        AiAgentTaskStepService.reset_steps(task, cls.step_defs)
        cls.dispatch(task.id)
        return task
