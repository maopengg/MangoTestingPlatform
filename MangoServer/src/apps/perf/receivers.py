from django.dispatch import receiver

from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.task_center.signals import executor_task_finished


@receiver(executor_task_finished, dispatch_uid="perf.reconcile_finished_executor_task")
def reconcile_finished_executor_task(*, task_type, business_id, **_kwargs):
    if task_type != ExecutorTaskTypeEnum.PERF_EXECUTION.value or not business_id:
        return

    from src.apps.perf.services.execution.recovery import PerfRecoveryService

    PerfRecoveryService.reconcile_executor_task(business_id)
