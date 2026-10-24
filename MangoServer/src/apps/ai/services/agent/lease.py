# -*- coding: utf-8 -*-
from datetime import timedelta
from threading import Event, Thread

from django.db import close_old_connections, transaction
from django.utils import timezone

from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.models import AiAgentTask


class AgentTaskLease:
    LEASE_SECONDS = 60
    HEARTBEAT_SECONDS = 10

    @classmethod
    def claim(cls, worker_id: str):
        now = timezone.now()
        with transaction.atomic():
            AiAgentTask.objects.filter(
                status__in=[
                    AiAgentTaskStatusEnum.CLAIMED.value,
                    AiAgentTaskStatusEnum.RUNNING.value,
                    AiAgentTaskStatusEnum.WAITING_MODEL.value,
                ],
                lease_expires_at__lt=now,
            ).update(
                status=AiAgentTaskStatusEnum.PENDING.value,
                worker_id=None,
                lease_expires_at=None,
            )
            task = (
                AiAgentTask.objects.select_for_update(skip_locked=True)
                .filter(status=AiAgentTaskStatusEnum.PENDING.value, cancel_requested=False)
                .order_by("id")
                .first()
            )
            if not task:
                return None
            task.status = AiAgentTaskStatusEnum.CLAIMED.value
            task.worker_id = worker_id
            task.heartbeat_at = now
            task.lease_expires_at = now + timedelta(seconds=cls.LEASE_SECONDS)
            task.attempt_no += 1
            task.save(
                update_fields=["status", "worker_id", "heartbeat_at", "lease_expires_at", "attempt_no", "update_time"])
            return task

    @classmethod
    def renew(cls, task_id: int, worker_id: str) -> bool:
        now = timezone.now()
        return bool(
            AiAgentTask.objects.filter(
                id=task_id,
                worker_id=worker_id,
                status__in=[AiAgentTaskStatusEnum.CLAIMED.value, AiAgentTaskStatusEnum.RUNNING.value,
                            AiAgentTaskStatusEnum.WAITING_MODEL.value],
            ).update(heartbeat_at=now, lease_expires_at=now + timedelta(seconds=cls.LEASE_SECONDS), update_time=now)
        )

    @classmethod
    def heartbeat(cls, task_id: int, worker_id: str):
        stop = Event()

        def beat():
            while not stop.wait(cls.HEARTBEAT_SECONDS):
                close_old_connections()
                if not cls.renew(task_id, worker_id):
                    break
            close_old_connections()

        thread = Thread(target=beat, name=f"agent-heartbeat-{task_id}", daemon=True)
        thread.start()
        return stop, thread
