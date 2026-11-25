# -*- coding: utf-8 -*-
from datetime import timedelta

from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionStatusEnum,
)
from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.system.enums.executor import ExecutorTaskStatusEnum
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
from src.apps.data_factory.schemas.cleanup_resource import CleanupReportOwner
from src.common.logging import log


class DataFactoryExecutionRecovery:
    """补偿进程中断遗漏的清理，并核对待手动清理数据。"""

    RUNNING_TIMEOUT_MINUTES = 30
    BATCH_SIZE = 100
    LEGACY_OVERDUE_ERROR = '执行数据超过 24 小时仍未清理，请核对后执行清理'

    @classmethod
    @transaction.atomic
    def fail_unverified_cleanup(cls, execution, message):
        # 与正常清理使用同一执行锁，复核和失败保存之间不允许成功结果被旧巡检覆盖。
        current = CleanupPersistenceService.lock_execution(execution.id)
        if DataFactoryCleanup.reconcile_verified_cleanup(current):
            return False
        DataFactoryCleanup.mark_execution_failed(current, message)
        return True

    @staticmethod
    def report_execution_ended(owner, execution):
        from mangotools.enums import TaskEnum
        from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
        from src.apps.test_center.enums import TestCaseTypeEnum
        detail = TestCenterQuerySelector.test_suite_details().filter(
            id=owner['parent_case_detail_id'], retry=owner['parent_attempt']).only('id', 'status', 'type', 'summary_data').first()
        from src.apps.test_center.services.reporting.test_suite.recovery import ReportRecoveryService
        control = ReportRecoveryService.read(detail.summary_data) if detail else None
        recovering_ended = bool(control and control.owner_ended and control.attempt == owner['parent_attempt'])
        if detail is None or (not recovering_ended and detail.status not in {
                TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value,
                TaskEnum.INFRASTRUCTURE_BLOCKED.value}):
            return False
        if detail.type == TestCaseTypeEnum.API.value:
            from src.apps.auto_api.selectors.querysets import ApiQuerySelector
            trace = ApiQuerySelector.api_case_execution_trace().filter(
                test_suite_detail_id=detail.id).order_by('-id').only(
                'started_at', 'finished_at', 'worker_name', 'summary').first()
            if trace is None or trace.started_at is None or trace.started_at > execution.create_time:
                return False
            if trace.finished_at is not None:
                return trace.finished_at >= execution.create_time
            from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
            summary = trace.summary if isinstance(trace.summary, dict) else {}
            return ApiWorkerRecoveryService.execution_owner_replaced(
                trace.worker_name, summary.get('execution_owner'), trace.started_at)
        return True

    @classmethod
    @transaction.atomic
    def recover_inline_cleanup(cls):
        interrupted = ExecutorTaskService.expire_inline_cleanup_tasks()
        failed = 0
        for execution in DataFactoryExecution.objects.filter(id__in=interrupted):
            if cls.fail_unverified_cleanup(
                    execution, '同步清理进程失联或阶段超时，结果需核查；请在执行记录核对后补清'):
                failed += 1
        return failed

    @classmethod
    def recover(cls) -> dict:
        interrupted_count = cls.recover_inline_cleanup()
        now = timezone.now()
        stale_running_before = now - timedelta(minutes=cls.RUNNING_TIMEOUT_MINUTES)
        automatic_cleanup_before = now - timedelta(minutes=cls.RUNNING_TIMEOUT_MINUTES)

        automatic_candidates = DataFactoryExecution.objects.filter(
            datafactoryexecutionitem__isnull=False,
        ).exclude(
            cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value,
        ).filter(
            Q(
                status=DataFactoryExecutionStatusEnum.PROCEED.value,
                update_time__lt=stale_running_before,
            )
            | Q(
                status=DataFactoryExecutionStatusEnum.FAIL.value,
                cleanup_status=DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
            )
            | Q(
                status=DataFactoryExecutionStatusEnum.SUCCESS.value,
                cleanup_status=DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
                update_time__lt=automatic_cleanup_before,
                datafactoryexecutionitem__cleanup_strategy=(
                    DataFactoryCleanupStrategyEnum.EXECUTION_END.value
                ),
            )
        ).distinct().order_by('id')[:cls.BATCH_SIZE]

        recovered = 0
        failed = interrupted_count
        queued = 0
        deferred = 0
        for execution in automatic_candidates:
            try:
                if DataFactoryCleanup.reconcile_verified_cleanup(execution):
                    recovered += 1
                    continue
                saved_owner = (execution.context or {}).get(CLEANUP_REPORT_CONTEXT_KEY)
                if not saved_owner:
                    from src.apps.data_factory.enums import DataFactoryExecutionSourceEnum
                    from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation
                    if (getattr(execution, 'source_type', None) == DataFactoryExecutionSourceEnum.TEMPLATE_DEBUG.value
                            and execution.status == DataFactoryExecutionStatusEnum.SUCCESS.value):
                        if not DataFactoryExecutionReconciliation.owner_ended(execution):
                            deferred += 1
                            log.system.warning('event=data_factory_debug_recovery_waiting_owner execution_id=%s '
                                               'action=verify_original_owner_before_handoff', execution.id)
                            continue
                        task = DataFactoryCleanupScheduleService.enqueue_debug_recovery(execution.id)
                        if task.status == ExecutorTaskStatusEnum.FAILED.value:
                            failed += 1
                        elif task.status == ExecutorTaskStatusEnum.SUCCESS.value:
                            recovered += 1
                        else:
                            queued += 1
                        continue
                    if execution.status == DataFactoryExecutionStatusEnum.PROCEED.value:
                        deferred += 1
                        log.system.warning('event=data_factory_recovery_unconfirmed_owner execution_id=%s '
                            'action=verify_original_execution_before_cleanup', execution.id)
                        continue
                    marked = cls.fail_unverified_cleanup(
                        execution, '执行已中断或自动清理未完成，请核对执行记录后补清；无正式报告不会转入调度队列')
                    failed += int(marked)
                    recovered += int(not marked)
                    continue
                owner = CleanupReportOwner.model_validate(saved_owner, strict=True).model_dump()
                DataFactoryCleanupScheduleService.validate_report_owner(owner, execution)
                if not cls.report_execution_ended(owner, execution):
                    deferred += 1
                    log.system.warning('event=data_factory_recovery_waiting_owner execution_id=%s '
                        'case_detail_id=%s attempt=%s action=wait_for_execution_end', execution.id,
                        owner['parent_case_detail_id'], owner['parent_attempt'])
                    continue
                if execution.status == DataFactoryExecutionStatusEnum.PROCEED.value:
                    execution.status = DataFactoryExecutionStatusEnum.FAIL.value
                    execution.error_message = '原报告执行已结束，平台按执行快照触发遗留数据清理补偿'
                    execution.save(update_fields=['status', 'error_message', 'update_time'])
                token = DataFactoryCleanupScheduleService.set_owner(
                    owner['parent_case_detail_id'], owner['parent_attempt'])
                try:
                    task = DataFactoryCleanupScheduleService.enqueue(execution.id)
                finally:
                    DataFactoryCleanupScheduleService.reset_owner(token)
                if task.status == ExecutorTaskStatusEnum.FAILED.value:
                    failed += 1
                elif task.status == ExecutorTaskStatusEnum.SUCCESS.value:
                    recovered += 1
                else:
                    queued += 1
            except Exception as error:
                error_message = f'数据工厂清理补偿异常：{error}'
                if not cls.fail_unverified_cleanup(execution, error_message):
                    recovered += 1
                    continue
                failed += 1
                log.system.error(
                    f'{error_message}，execution_id={execution.id}'
                )

        manual_cleanup = cls.reconcile_manual_cleanup_states()
        from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation
        reconciliation = DataFactoryExecutionReconciliation.reconcile()
        return {
            **reconciliation,
            'data_factory_recovery_count': recovered,
            'data_factory_recovery_failed_count': failed,
            'data_factory_recovery_queued_count': queued,
            'data_factory_recovery_deferred_count': deferred,
            'data_factory_residual_todo_count': manual_cleanup['pending'],
            'data_factory_residual_resolved_count': manual_cleanup['resolved'],
        }

    @classmethod
    def reconcile_manual_cleanup_states(cls) -> dict[str, int]:
        """核对手动清理数据；仅真实残留进入“需要清理”，不冒充 SQL 清理失败。"""
        executions = DataFactoryExecution.objects.filter(
            status=DataFactoryExecutionStatusEnum.SUCCESS.value,
        ).filter(
            Q(
                datafactoryexecutionitem__cleanup_strategy=(
                    DataFactoryCleanupStrategyEnum.MANUAL.value
                ),
                datafactoryexecutionitem__cleanup_status__in=[
                    DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
                    DataFactoryCleanupStatusEnum.SKIPPED.value,
                ],
            )
            | Q(
                datafactoryexecutionitem__cleanup_strategy=(
                    DataFactoryCleanupStrategyEnum.MANUAL.value
                ),
                datafactoryexecutionitem__cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
                datafactoryexecutionitem__cleanup_error=cls.LEGACY_OVERDUE_ERROR,
            )
            | Q(
                datafactoryexecutionitem__cleanup_strategy=(
                    DataFactoryCleanupStrategyEnum.NONE.value
                ),
                datafactoryexecutionitem__cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
                datafactoryexecutionitem__cleanup_error=cls.LEGACY_OVERDUE_ERROR,
            )
        ).distinct().order_by('update_time', 'id')[:cls.BATCH_SIZE]
        pending = 0
        resolved = 0
        for execution in executions:
            items = list(
                DataFactoryExecutionItem.objects.select_related(
                    'execution',
                    'template__entity',
                    'database',
                    'datasource_binding__datasource_alias',
                    'datasource_binding__database',
                    'datasource_binding__test_object',
                ).filter(execution=execution).order_by('id')
            )
            for item in items:
                if item.cleanup_strategy == DataFactoryCleanupStrategyEnum.NONE.value:
                    if (
                            item.cleanup_status == DataFactoryCleanupStatusEnum.FAIL.value
                            and item.cleanup_error == cls.LEGACY_OVERDUE_ERROR
                    ):
                        DataFactoryCleanup.mark_skipped(item)
                    continue
                if item.cleanup_strategy != DataFactoryCleanupStrategyEnum.MANUAL.value:
                    continue
                if (
                        item.cleanup_status == DataFactoryCleanupStatusEnum.FAIL.value
                        and item.cleanup_error != cls.LEGACY_OVERDUE_ERROR
                ):
                    continue
                try:
                    exists = DataFactoryCleanup.manual_cleanup_item_exists(item)
                except Exception as error:
                    DataFactoryCleanup.mark_pending_manual(item)
                    log.system.error(
                        '核对数据工厂待手动清理数据失败，'
                        f'execution_id={execution.id}，item_id={item.id}，错误：{error}'
                    )
                else:
                    if exists:
                        DataFactoryCleanup.mark_pending_manual(item)
                    else:
                        DataFactoryCleanup.mark_success(item)

            statuses = {item.cleanup_status for item in items}
            if DataFactoryCleanupStatusEnum.FAIL.value in statuses:
                execution.cleanup_status = DataFactoryCleanupStatusEnum.FAIL.value
            elif DataFactoryCleanupStatusEnum.PENDING_MANUAL.value in statuses:
                execution.cleanup_status = DataFactoryCleanupStatusEnum.PENDING_MANUAL.value
                execution.cleanup_time = None
                pending += 1
            elif DataFactoryCleanupStatusEnum.NOT_CLEANED.value in statuses:
                execution.cleanup_status = DataFactoryCleanupStatusEnum.NOT_CLEANED.value
            elif statuses and statuses == {DataFactoryCleanupStatusEnum.SKIPPED.value}:
                execution.cleanup_status = DataFactoryCleanupStatusEnum.SKIPPED.value
                execution.cleanup_time = timezone.now()
                resolved += 1
            else:
                execution.cleanup_status = DataFactoryCleanupStatusEnum.SUCCESS.value
                execution.cleanup_time = timezone.now()
                resolved += 1
            if execution.error_message == cls.LEGACY_OVERDUE_ERROR:
                execution.error_message = None
            DataFactoryCleanup.clear_resolved_cleanup_error(execution)
            execution.save(update_fields=[
                'cleanup_status',
                'cleanup_time',
                'error_message',
                'update_time',
            ])
            DataFactoryCleanup.sync_workbench_todo(execution)
        return {'pending': pending, 'resolved': resolved}
