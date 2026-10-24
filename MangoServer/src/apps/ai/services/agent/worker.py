# -*- coding: utf-8 -*-
import socket
import uuid

from django.db import close_old_connections

from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent
from src.apps.ai.agent.functional_case.agent import FunctionalCaseAgent
from src.apps.ai.enums import AiAgentTaskStatusEnum, AiAgentTaskTypeEnum
from src.apps.ai.models import AiAgentTask
from src.apps.ai.services.agent.lease import AgentTaskLease
from src.apps.ai.services.core import AiTaskService
from src.apps.ai.services.harness.artifact import AgentEventService

AGENT_REGISTRY = {
    AiAgentTaskTypeEnum.MANUAL_CASE_SYNC.value: FunctionalCaseAgent,
    AiAgentTaskTypeEnum.GENERATE_API_CASE.value: ApiAutomationAgent,
}


class AgentWorkerService:
    def __init__(self, worker_id: str | None = None):
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    def run_once(self) -> bool:
        close_old_connections()
        task = AgentTaskLease.claim(self.worker_id)
        if not task:
            return False
        agent = AGENT_REGISTRY.get(task.task_type)
        if not agent:
            AiTaskService.fail_task(task, f"未注册的 Agent 任务类型：{task.task_type}")
            return True
        stop, heartbeat = AgentTaskLease.heartbeat(task.id, self.worker_id)
        try:
            task.status = AiAgentTaskStatusEnum.RUNNING.value
            task.save(update_fields=["status", "update_time"])
            AgentEventService.emit(task, "task_started", "Agent Worker 已开始执行")
            agent.run(task)
        except Exception as exc:
            task.refresh_from_db()
            if task.status not in [AiAgentTaskStatusEnum.FAIL.value, AiAgentTaskStatusEnum.CANCELLED.value]:
                AiTaskService.fail_task(task, str(exc))
            AgentEventService.emit(task, "task_failed", str(exc))
        finally:
            stop.set()
            heartbeat.join(timeout=2)
            AiAgentTask.objects.filter(id=task.id, worker_id=self.worker_id).update(
                worker_id=None,
                lease_expires_at=None,
            )
            close_old_connections()
        return True
