from django.db import transaction

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.exceptions import (
    MONITORING_SERVICE_EXECUTION_MONITORING_INVALID,
    MONITORING_TASK_EXECUTION_MONITORING_DUPLICATED,
    MonitoringError,
)
from src.apps.monitoring.models import MonitoringTask
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService


class MonitoringTaskControlService:
    @classmethod
    def request_start(cls, task: MonitoringTask) -> MonitoringTask:
        if ServiceHeartbeatService.count_online_instances(RuntimeServiceName.MONITORING) <= 0:
            raise MonitoringError(MONITORING_SERVICE_EXECUTION_MONITORING_INVALID)

        with transaction.atomic():
            locked_task = MonitoringTask.objects.select_for_update().get(id=task.id)
            if locked_task.status in {
                MonitoringTaskStatusEnum.STARTING.value,
                MonitoringTaskStatusEnum.RUNNING.value,
            }:
                raise MonitoringError(MONITORING_TASK_EXECUTION_MONITORING_DUPLICATED)
            locked_task.status = MonitoringTaskStatusEnum.STARTING.value
            locked_task.pid = None
            locked_task.exit_code = None
            locked_task.started_at = None
            locked_task.stopped_at = None
            locked_task.save(
                update_fields=[
                    'status',
                    'pid',
                    'exit_code',
                    'started_at',
                    'stopped_at',
                    'update_time',
                ]
            )
            return locked_task
