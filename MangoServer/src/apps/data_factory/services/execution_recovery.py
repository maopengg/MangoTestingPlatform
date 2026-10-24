# -*- coding: utf-8 -*-
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionStatusEnum,
)
from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.common.logging import log


class DataFactoryExecutionRecovery:
    """补偿进程中断遗漏的清理，并核对待手动清理数据。"""

    RUNNING_TIMEOUT_MINUTES = 30
    BATCH_SIZE = 100
    LEGACY_OVERDUE_ERROR = '执行数据超过 24 小时仍未清理，请核对后执行清理'

    @classmethod
    def recover(cls) -> dict:
        now = timezone.now()
        stale_running_before = now - timedelta(minutes=cls.RUNNING_TIMEOUT_MINUTES)
        automatic_cleanup_before = now - timedelta(minutes=cls.RUNNING_TIMEOUT_MINUTES)

        automatic_candidates = DataFactoryExecution.objects.filter(
            datafactoryexecutionitem__isnull=False,
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
        failed = 0
        for execution in automatic_candidates:
            if execution.status == DataFactoryExecutionStatusEnum.PROCEED.value:
                execution.status = DataFactoryExecutionStatusEnum.FAIL.value
                execution.error_message = '执行进程中断或超时，平台已触发数据清理补偿'
                execution.save(update_fields=['status', 'error_message', 'update_time'])
            try:
                result = DataFactoryCleanup.cleanup_execution(
                    execution.id,
                    force_cleanup=True,
                    allow_missing=True,
                )
                if result.get('fail'):
                    failed += 1
                else:
                    recovered += 1
            except Exception as error:
                failed += 1
                error_message = f'数据工厂清理补偿异常：{error}'
                DataFactoryCleanup.mark_execution_failed(execution, error_message)
                log.system.error(
                    f'{error_message}，execution_id={execution.id}'
                )

        manual_cleanup = cls.reconcile_manual_cleanup_states()
        return {
            'data_factory_recovery_count': recovered,
            'data_factory_recovery_failed_count': failed,
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
            execution.save(update_fields=[
                'cleanup_status',
                'cleanup_time',
                'error_message',
                'update_time',
            ])
            DataFactoryCleanup.sync_workbench_todo(execution)
        return {'pending': pending, 'resolved': resolved}
