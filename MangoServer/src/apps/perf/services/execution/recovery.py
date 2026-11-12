from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from src.apps.perf.enums import PerfRunNodeErrorCodeEnum, PerfRunNodeStatusEnum, PerfRunStatusEnum
from src.apps.perf.models import PerfRun, PerfRunEvent, PerfRunNode
from src.apps.perf.services.capacity.capacity import PerfCapacityService
from src.apps.perf.services.execution.execution import PerfExecutionService
from src.apps.perf.services.execution.finalize import PerfFinalizeService
from src.apps.system.enums import ExecutorTaskStatusEnum
from src.apps.system.enums import RuntimeServiceName
from src.common.decorators.system_error import report_system_error
from src.common.enums.system_error import SystemErrorEventSource
from src.common.logging import log


class PerfRecoveryService:
    NODE_HEARTBEAT_TIMEOUT_SECONDS = 90
    STARTUP_GRACE_SECONDS = 180
    RUN_GRACE_SECONDS = 300

    @classmethod
    def recover(cls):
        now = timezone.now()
        waiting_ids = list(PerfRun.objects.filter(
            status=PerfRunStatusEnum.WAITING_EXECUTOR.value,
            update_time__lte=now - timedelta(seconds=30),
        ).values_list("id", flat=True)[:100])
        for run_id in waiting_ids:
            try:
                PerfExecutionService.dispatch_run(run_id)
            except Exception as error:
                cls._report_recovery_error(error, 'retry_performance_dispatch')
                log.system.warning(f"性能运行 {run_id} 等待执行器重试失败: {error}")

        node_ids = list(PerfRunNode.objects.filter(
            status__in=[PerfRunNodeStatusEnum.DISPATCHED.value, PerfRunNodeStatusEnum.READY.value,
                        PerfRunNodeStatusEnum.RUNNING.value],
        ).values_list("id", flat=True)[:1000])
        for node_id in node_ids:
            cls._recover_node(node_id, now)

        PerfCapacityService.expire()

    @classmethod
    @transaction.atomic
    def _recover_node(cls, node_id: int, now):
        node = PerfRunNode.objects.select_for_update().select_related("run", "executor_task").filter(id=node_id).first()
        if not node or node.status in PerfRunNodeStatusEnum.terminal_values():
            return
        if cls._reconcile_terminal_executor_task(node, now):
            return
        if node.status == PerfRunNodeStatusEnum.DISPATCHED.value:
            deadline = (node.run.schedule_at or node.create_time) + timedelta(seconds=cls.STARTUP_GRACE_SECONDS)
        else:
            anchor = node.last_heartbeat_at or node.started_at or node.ready_at or node.update_time
            deadline = anchor + timedelta(seconds=cls.NODE_HEARTBEAT_TIMEOUT_SECONDS)
        hard_deadline = (node.run.schedule_at or node.run.create_time) + timedelta(
            seconds=node.run.duration_seconds + cls.RUN_GRACE_SECONDS
        )
        if now <= deadline and now <= hard_deadline:
            return
        node.status = PerfRunNodeStatusEnum.TIMEOUT.value
        node.finished_at = now
        node.error_code = PerfRunNodeErrorCodeEnum.EXECUTOR_HEARTBEAT_TIMEOUT.value
        node.error_message = "执行器启动、心跳或运行结果超过允许时限"
        node.save(update_fields=["status", "finished_at", "error_code", "error_message", "update_time"])
        PerfRunEvent.objects.create(
            run=node.run, run_node=node, event_type="node_timeout", level="error",
            message="性能执行节点超时", detail={}, occurred_at=now,
        )
        if not node.run.nodes.exclude(status__in=PerfRunNodeStatusEnum.terminal_values()).exists():
            node.run.status = PerfRunStatusEnum.AGGREGATING.value
            node.run.finished_at = now
            node.run.revision += 1
            node.run.save(update_fields=["status", "finished_at", "revision", "update_time"])
            transaction.on_commit(lambda: cls.safe_finalize(node.run_id))

    @classmethod
    @transaction.atomic
    def reconcile_executor_task(cls, node_id: int, now=None) -> bool:
        node = PerfRunNode.objects.select_for_update().select_related("run", "executor_task").filter(id=node_id).first()
        if not node or node.status in PerfRunNodeStatusEnum.terminal_values():
            return False
        return cls._reconcile_terminal_executor_task(node, now or timezone.now())

    @classmethod
    def _reconcile_terminal_executor_task(cls, node: PerfRunNode, now) -> bool:
        task = node.executor_task
        if not task or task.status not in ExecutorTaskStatusEnum.terminal_values():
            return False
        status_map = {
            ExecutorTaskStatusEnum.CANCELLED.value: PerfRunNodeStatusEnum.CANCELLED.value,
            ExecutorTaskStatusEnum.TIMEOUT.value: PerfRunNodeStatusEnum.TIMEOUT.value,
        }
        node.status = status_map.get(task.status, PerfRunNodeStatusEnum.FAILED.value)
        node.finished_at = task.finished_at or now
        node.error_code = task.error_code or "executor_task_ended_without_node_result"
        node.error_message = task.error_message or "执行器任务已结束，但未回传性能节点结果"
        node.save(update_fields=["status", "finished_at", "error_code", "error_message", "update_time"])
        PerfRunEvent.objects.create(
            run=node.run,
            run_node=node,
            event_type="node_executor_task_failed",
            level="error",
            message="执行器任务结束但性能节点未回传结果",
            detail={"executor_task_id": task.id, "executor_task_status": task.status},
            occurred_at=now,
        )
        if node.run.nodes.exclude(status__in=PerfRunNodeStatusEnum.terminal_values()).exists():
            return True
        if node.run.status in PerfRunStatusEnum.terminal_values():
            PerfCapacityService.release(node.run_id)
            return True
        node.run.status = PerfRunStatusEnum.AGGREGATING.value
        node.run.finished_at = node.finished_at
        node.run.error_code = node.error_code
        node.run.error_message = node.error_message
        node.run.summary = {
            "node_count": node.run.nodes.count(),
            "has_node_failure": True,
        }
        node.run.revision += 1
        node.run.save(update_fields=[
            "status", "finished_at", "error_code", "error_message", "summary", "revision", "update_time",
        ])
        transaction.on_commit(lambda: cls.safe_finalize(node.run_id))
        return True

    @staticmethod
    def safe_finalize(run_id: int):
        try:
            PerfFinalizeService.finalize(run_id)
        except Exception as error:
            PerfRecoveryService._report_recovery_error(error, 'finalize_performance_run')
            log.system.error(f"性能运行 {run_id} 汇总失败: {error}")

    @staticmethod
    def _report_recovery_error(error: Exception, operation: str) -> None:
        report_system_error(
            error,
            source=SystemErrorEventSource.PERFORMANCE,
            request_path=operation,
            service_name=RuntimeServiceName.SCHEDULER,
        )
