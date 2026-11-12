import socket
from typing import Any

import time
from django.utils import timezone

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.selectors.querysets import MonitoringQuerySelector
from src.apps.monitoring.services.execution.runner import MonitoringTaskRunner
from src.apps.monitoring.services.diagnostics.task_diagnostic import MonitoringTaskDiagnosticService
from src.apps.monitoring.services.execution.script_capabilities import MonitoringScriptCapabilitiesService
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.common.decorators.retry import async_task_db_connection
from src.common.decorators.system_error import system_error_guard
from src.common.logging import log

runner = MonitoringTaskRunner()


class MonitoringRuntimeService:
    def __init__(self, instance_name: str | None = None, poll_interval: float = 2.0):
        self.instance_name = instance_name or socket.gethostname()
        self.poll_interval = max(0.5, poll_interval)
        self.running = True

    @system_error_guard(
        source=SystemErrorEventSource.MONITORING,
        request_path='run_monitoring_service',
        service_name=RuntimeServiceName.MONITORING,
    )
    def run_forever(self) -> None:
        log.monitoring.info(f'monitoring-service 启动：instance={self.instance_name}')
        runner.restore_running_tasks()
        try:
            while self.running:
                self.reconcile()
                ServiceHeartbeatService.beat_if_due(
                    self,
                    RuntimeServiceName.MONITORING,
                    instance_name=self.instance_name,
                    metadata={
                        'active_tasks': len(runner.active_task_ids()),
                        'poll_interval': self.poll_interval,
                        'monitoring_script_capabilities': MonitoringScriptCapabilitiesService.inspect_local(),
                    },
                )
                time.sleep(self.poll_interval)
        finally:
            runner.stop_all_tasks(timeout=5.0)
            log.monitoring.info(f'monitoring-service 已停止：instance={self.instance_name}')

    def stop(self) -> None:
        self.running = False

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def reconcile(self) -> None:
        active_ids = runner.active_task_ids()
        desired_running = {
            task.id: task
            for task in MonitoringQuerySelector.monitoring_task().filter(
                status__in=[
                    MonitoringTaskStatusEnum.STARTING.value,
                    MonitoringTaskStatusEnum.RUNNING.value,
                ]
            )
        }
        for task_id, task in desired_running.items():
            if task_id not in active_ids:
                try:
                    self.start_task(task)
                except Exception as error:
                    log.monitoring.error(f'监控任务启动失败：task={task_id}, type={type(error).__name__}')
                    task.status = MonitoringTaskStatusEnum.FAILED.value
                    task.pid = None
                    task.exit_code = -1
                    task.stopped_at = timezone.now()
                    task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
                    MonitoringTaskDiagnosticService.record(task, f'监控任务启动失败：{type(error).__name__}: {error}')
                    try:
                        runner.append_task_log(task, f'监控任务启动失败：{type(error).__name__}')
                    except Exception:
                        log.monitoring.warning(f'任务文件日志不可写，失败原因已尝试保存至监控报告：task={task_id}')
        for task_id in active_ids - set(desired_running):
            task = MonitoringQuerySelector.monitoring_task().filter(id=task_id).first()
            if task is not None:
                runner.stop_task(task, timeout=5.0, update_status=False)
            else:
                runner.stop_task_by_id(task_id, timeout=5.0)

    @staticmethod
    @system_error_guard(
        source=SystemErrorEventSource.MONITORING,
        request_path='start_monitoring_task',
        service_name=RuntimeServiceName.MONITORING,
    )
    def start_task(task: Any) -> None:
        runner.start_task(task)
