from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from src.apps.data_factory.constants import (CLEANUP_REPORT_CONTEXT_KEY, EXECUTION_OWNER_CONTEXT_KEY,
                                           EXECUTION_RECONCILIATION_CONTEXT_KEY)
from src.apps.data_factory.enums import DataFactoryExecutionStatusEnum, DataFactoryCleanupStatusEnum
from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.schemas.cleanup_resource import FactoryExecutionOwner, FactoryExecutionReconciliation
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
from src.common.logging import log


class DataFactoryExecutionReconciliation:
    BATCH_SIZE = 100

    @staticmethod
    def owner_ended(execution):
        from src.apps.auto_api.selectors.querysets import ApiQuerySelector
        from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
        raw = (execution.context or {}).get(EXECUTION_OWNER_CONTEXT_KEY)
        if not raw:
            saved_report = (execution.context or {}).get(CLEANUP_REPORT_CONTEXT_KEY)
            if saved_report:
                from src.apps.data_factory.schemas.cleanup_resource import CleanupReportOwner
                from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
                from src.apps.data_factory.services.recovery.execution_recovery import DataFactoryExecutionRecovery
                try:
                    report = CleanupReportOwner.model_validate(saved_report, strict=True).model_dump()
                except ValidationError:
                    return False
                DataFactoryCleanupScheduleService.validate_report_owner(report, execution)
                return DataFactoryExecutionRecovery.report_execution_ended(report, execution)
            return False
        try:
            owner = FactoryExecutionOwner.model_validate(raw)
        except ValidationError:
            return False
        if owner.trace_id and owner.trace_key:
            trace = ApiQuerySelector.api_case_execution_trace().filter(
                id=owner.trace_id, trace_id=owner.trace_key,
                started_at__lte=execution.create_time).only('finished_at', 'summary').first()
            if trace and (trace.summary or {}).get('execution_owner', {}).get('process_token') == owner.process_token:
                if trace.finished_at and trace.finished_at >= execution.create_time:
                    return True
        identity = owner.model_dump()
        return bool(ServiceHeartbeatService.completed_mcp_process(identity, execution.create_time)
                    or ApiWorkerRecoveryService.execution_owner_replaced(owner.worker_name, identity, execution.create_time))

    @staticmethod
    def fully_verified(items):
        if not items:
            return False
        for item in items:
            if item.cleanup_status != DataFactoryCleanupStatusEnum.SUCCESS.value:
                return False
            state = DataFactoryCleanupResourceService.state(item)
            if state.unknown_permits:
                return False
            if state.snapshots and (not state.sql_cleaned or
                    any(not any(result.success and result.index == snapshot.index
                                and result.document_id == snapshot.document_id for result in state.results)
                        for snapshot in state.snapshots)):
                return False
            uncertain = {value.request_id for value in state.uncertain_requests}
            if uncertain:
                from src.apps.data_factory.models import SqlExecutionRecord
                records = dict(SqlExecutionRecord.objects.filter(request_id__in=uncertain).values_list(
                    'request_id', 'source_detail'))
                if set(records) != uncertain or any(
                        details.get('outcome_unknown') is not False and
                        (details.get('outcome_resolution') or {}).get('basis') != 'owned_resource_verified'
                        for details in records.values()):
                    return False
        return True

    @staticmethod
    def save_evidence(execution, reason):
        if execution.error_message and len(execution.error_message) > 1000:
            # 不能为收敛展示状态截断唯一的原错误证据。
            return False
        evidence = FactoryExecutionReconciliation(checked_at=timezone.now().isoformat(), reason=reason,
            previous_error=execution.error_message or None)
        execution.context = {**(execution.context or {}),
                             EXECUTION_RECONCILIATION_CONTEXT_KEY: evidence.model_dump(mode='json')}
        return True

    @classmethod
    def reconcile_empty(cls, execution):
        if not cls.owner_ended(execution):
            return False
        with transaction.atomic():
            current = DataFactoryExecution.objects.select_for_update(skip_locked=True).filter(
                id=execution.id, update_time=execution.update_time,
                status__in=[DataFactoryExecutionStatusEnum.PROCEED.value,
                            DataFactoryExecutionStatusEnum.PENDING.value]).first()
            if current is None or DataFactoryExecutionItem.objects.filter(execution_id=current.id).exists():
                return False
            if not cls.save_evidence(current, 'original_owner_ended_without_registered_items'):
                return False
            current.status = DataFactoryExecutionStatusEnum.FAIL.value
            # 空台账不等于零残留。只关闭“仍在创建”，不自动清理、核销或宣称清理成功。
            current.error_message = '原执行已确认结束，但没有已登记的创建明细；需核查原请求结果及残留，平台未重放创建或删除'
            current.save(update_fields=['status', 'error_message', 'context', 'update_time'])
        log.system.info('event=data_factory_execution_reconciled execution_id=%s reason=owner_ended_empty_review',
                        execution.id)
        return True

    @classmethod
    def reconcile_cleaned(cls, execution):
        with transaction.atomic():
            current = DataFactoryExecution.objects.select_for_update(skip_locked=True).filter(
                id=execution.id, update_time=execution.update_time,
                status=DataFactoryExecutionStatusEnum.SUCCESS.value,
                cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).first()
            if current is None:
                return False
            items = list(DataFactoryExecutionItem.objects.filter(execution_id=current.id))
            if not cls.fully_verified(items):
                return False
            if not cls.save_evidence(current, 'all_registered_resources_verified_cleaned'):
                return False
            DataFactoryCleanup.clear_resolved_cleanup_error(current)
            current.save(update_fields=['error_message', 'context', 'update_time'])
            transaction.on_commit(lambda: DataFactoryCleanup.sync_workbench_todo(current))
        log.system.info('event=data_factory_execution_reconciled execution_id=%s reason=verified_cleanup_error_resolved',
                        execution.id)
        return True

    @classmethod
    def reconcile(cls):
        stale = timezone.now() - timedelta(minutes=30)
        empty = DataFactoryExecution.objects.filter(
            status__in=[DataFactoryExecutionStatusEnum.PENDING.value, DataFactoryExecutionStatusEnum.PROCEED.value],
            update_time__lt=stale, datafactoryexecutionitem__isnull=True).order_by('id')[:cls.BATCH_SIZE]
        cleaned = DataFactoryExecution.objects.filter(
            status=DataFactoryExecutionStatusEnum.SUCCESS.value,
            cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value,
            error_message__isnull=False).exclude(error_message='').order_by('id')[:cls.BATCH_SIZE]
        counts = {'empty_execution_closed': 0, 'cleanup_error_resolved': 0, 'execution_review_required': 0}
        for candidates, handler, key in ((empty, cls.reconcile_empty, 'empty_execution_closed'),
                                          (cleaned, cls.reconcile_cleaned, 'cleanup_error_resolved')):
            for execution in candidates:
                try:
                    changed = handler(execution)
                    counts[key] += int(changed)
                    counts['execution_review_required'] += int(not changed)
                except Exception as error:
                    counts['execution_review_required'] += 1
                    log.system.warning('event=data_factory_reconciliation_deferred execution_id=%s exception_type=%s',
                                       execution.id, type(error).__name__)
        return counts
