"""Write operations for AI agent task lifecycle."""

from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.models import AiAgentTask
from src.apps.ai.services.harness.artifact import AgentEventService


class AiAgentTaskMutationService:
    @staticmethod
    def cancel(task: AiAgentTask) -> AiAgentTask:
        task.cancel_requested = True
        if task.status == AiAgentTaskStatusEnum.PENDING.value:
            task.status = AiAgentTaskStatusEnum.CANCELLED.value
        task.save(update_fields=["cancel_requested", "status", "update_time"])
        return task

    @staticmethod
    def confirm(task: AiAgentTask, confirmation: dict) -> AiAgentTask:
        task.status = AiAgentTaskStatusEnum.PENDING.value
        task.input_data = {**(task.input_data or {}), "confirmation": confirmation}
        task.save(update_fields=["status", "input_data", "update_time"])
        AgentEventService.emit(task, "confirmation_received", "已收到用户确认，任务重新进入队列")
        return task


__all__ = ["AiAgentTaskMutationService"]
