# -*- coding: utf-8 -*-
from threading import Thread

from django.db import close_old_connections

from src.apps.ai.agent.task_step import AiAgentTaskStepService
from src.apps.ai.models import AiAgentTask
from src.apps.ai.service.core import AiTaskService
from src.common.enums.ai_enum import AiAgentTaskStatusEnum


class BaseAgent:
    task_type: int | None = None
    step_defs: list[dict] = []

    @classmethod
    def create_task(cls, title: str, input_data: dict, user_id: int | None = None, skill=None) -> AiAgentTask:
        task = AiTaskService.create_task(cls.task_type, title, input_data, user_id=user_id, skill=skill)
        AiAgentTaskStepService.create_steps(task, cls.step_defs)
        return task

    @classmethod
    def dispatch(cls, task_id: int):
        Thread(target=cls.run_safely, args=(task_id,), daemon=True).start()

    @classmethod
    def run_safely(cls, task_id: int):
        close_old_connections()
        task = None
        try:
            task = AiAgentTask.objects.get(id=task_id, task_type=cls.task_type)
            AiTaskService.mark_running(task)
            cls.run(task)
        except Exception as exc:
            if task:
                AiTaskService.fail_task(task, str(exc))
        finally:
            if task:
                AiTaskService.clear_running(task)
            close_old_connections()

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
        if task.status == AiAgentTaskStatusEnum.RUNNING.value:
            raise ValueError("当前任务正在运行中，请等待完成后再操作")
        if input_patch:
            input_data = dict(task.input_data or {})
            input_data.update(input_patch)
            task.input_data = input_data
        task.status = AiAgentTaskStatusEnum.RUNNING.value
        task.error_message = None
        task.output_data = {}
        task.save(update_fields=["status", "error_message", "output_data", "input_data", "update_time"])
        cls.dispatch(task.id)
        return task
