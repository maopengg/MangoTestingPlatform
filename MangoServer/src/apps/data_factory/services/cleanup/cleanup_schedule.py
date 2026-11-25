from datetime import datetime, timedelta, timezone as datetime_timezone
from contextvars import ContextVar
from contextlib import contextmanager
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
import threading

from django.utils import timezone
from django.db import transaction
from django.conf import settings
from pydantic import ValidationError

from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStrategyEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.exceptions import DATA_FACTORY_CLEANUP_INTERRUPTED, DATA_FACTORY_CLEANUP_TIMEOUT
from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.system.enums.executor import ExecutorTaskStatusEnum
from src.apps.data_factory.schemas.cleanup_resource import CleanupTaskPayload, CleanupTaskProgress
from src.apps.data_factory.schemas.cleanup_resource import CleanupReportOwner
from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY, EXECUTION_OWNER_CONTEXT_KEY, EXECUTION_AUDIT_CONTEXT_KEY
from src.apps.data_factory.constants import ES_CLEANUP_PROBE_BATCH_SIZE, ES_CLEANUP_PROBE_WORKERS, ES_CLEANUP_RESOURCES_PER_WORKER
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum
from src.common.logging import log

_case_cleanup_owner = ContextVar('case_cleanup_owner', default=None)
_parent_wait_pulse = ContextVar('cleanup_parent_wait_pulse', default=None)
_probe_worker_budget = ContextVar('cleanup_probe_worker_budget', default=ES_CLEANUP_PROBE_WORKERS)
_inline_observation_items = ContextVar('inline_cleanup_observation_items', default=None)


class DataFactoryCleanupScheduleService:
    @classmethod
    def observation_items(cls, execution_id, lease, *, inline):
        cached = _inline_observation_items.get() if inline else None
        key = (execution_id, lease.task_id, lease.generation, getattr(lease, 'token', None))
        if cached is not None and cached.get('key') == key:
            return cached['items']
        from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
        items = list(DataFactoryQuerySelector.cleanup_observation_items(execution_id))
        if cached is not None:
            cached.clear()
            cached.update(key=key, items=items)
        return items

    @staticmethod
    def interval_union(values):
        merged = []
        for start, end in sorted(values):
            if end <= start:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        return merged

    @classmethod
    def probe_observations(cls, pending, lease):
        """同一租约内有界推进到期资源；SQL 删除顺序不变，子线程不领取其他任务。"""
        now = cls.server_now().timestamp()
        due = sorted((value for value in pending if value[1] <= now), key=lambda value: (value[1], value[0].id))[:ES_CLEANUP_PROBE_BATCH_SIZE]
        if not due:
            return pending, 0.0
        workers = min(_probe_worker_budget.get(), DatasourceGovernorService.policy().pool_size, len(due))
        if workers == 1:
            next_values = []
            for item, _ in due:
                next_at = DataFactoryCleanupResourceService.advance(
                    item, generation=lease.generation, task_id=lease.task_id, clock=cls.server_now)
                if next_at is None:
                    DataFactoryCleanup.mark_success(item)
                else:
                    next_values.append((item, next_at))
            selected = {item.id for item, _ in due}
            return [(value, at) for value, at in pending if value.id not in selected] + next_values, 0.0

        def probe(item):
            from django.db import close_old_connections, connections
            started = monotonic()
            error, next_at = None, None
            # 不复制 Case 的 greenlet、连接或等待回调；只传递原清理租约及持久资源快照。
            with DatasourceInfrastructureService.maintenance_scope(), DatasourceWaitService.owner(None), \
                    DatasourceWaitService.intervals() as waits, CleanupPersistenceService.lease(lease):
                try:
                    close_old_connections()
                    next_at = DataFactoryCleanupResourceService.advance(
                        item, generation=lease.generation, task_id=lease.task_id, clock=cls.server_now)
                except Exception as caught:
                    DatasourceInfrastructureService.capture(caught, result_unknown=True)
                    error = caught
                finally:
                    try:
                        connections.close_all()
                    except Exception as caught:
                        DatasourceInfrastructureService.capture(caught, result_unknown=True)
                        error = error or caught
                return item, next_at, error, DatasourceInfrastructureService.current(), started, monotonic(), waits

        # 在全部已发送采样收尾前不释放任务，也不让异常分支与子线程并行改写执行终态。
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='factory-es-probe') as executor:
            results = list(executor.map(probe, (item for item, _ in due)))
        selected, spans, active, failure = set(), [], [], None
        for item, next_at, error, issues, started, finished, waits in results:
            selected.add(item.id)
            DatasourceInfrastructureService.absorb(issues)
            spans.append((started, finished))
            cursor = started
            for left, right in cls.interval_union(waits):
                left, right = max(started, left), min(finished, right)
                if left > cursor:
                    active.append((cursor, left))
                cursor = max(cursor, right)
            if cursor < finished:
                active.append((cursor, finished))
            if error is not None:
                failure = failure or error
            else:
                DataFactoryCleanupResourceService.resolve_verified(DataFactoryCleanupResourceService.state(item))
                if next_at is None:
                    DataFactoryCleanup.mark_success(item)
        if failure is not None:
            raise failure
        remaining = [(item, at) for item, at in pending if item.id not in selected]
        remaining.extend((item, at) for item, at, error, *_ in results if error is None and at is not None)
        # 并行等待不能相加扣减：仅排除所有在途采样均在等待的墙钟时间。
        waited = sum(end - start for start, end in cls.interval_union(spans)) - sum(
            end - start for start, end in cls.interval_union(active))
        log.system.debug('event=factory_cleanup_probe_batch task_id=%s generation=%s probes=%s workers=%s '
                         'remaining=%s oldest_due_lag_seconds=%.3f all_waiting_seconds=%.3f',
                         lease.task_id, lease.generation, len(due), workers, len(remaining),
                         max(0, now - due[0][1]), max(0, waited))
        return remaining, max(0, waited)

    @staticmethod
    def current_owner():
        value = _case_cleanup_owner.get()
        return CleanupReportOwner.model_validate(value, strict=True).model_dump() if value is not None else None

    @classmethod
    def execution_context(cls, context):
        import os
        import socket
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        from src.apps.auto_api.services.execution_trace.recorder import current_execution_trace
        from src.apps.data_factory.schemas.cleanup_resource import FactoryExecutionOwner
        value = deepcopy(context or {})
        value.pop(CLEANUP_REPORT_CONTEXT_KEY, None)
        value.pop(EXECUTION_AUDIT_CONTEXT_KEY, None)
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
        from src.apps.data_factory.schemas.execution_audit import DatasourceAuditOrigin
        source = SqlExecutionAuditService.current_source()
        value[EXECUTION_AUDIT_CONTEXT_KEY] = DatasourceAuditOrigin(**{
            key: source[key] for key in DatasourceAuditOrigin.model_fields if source.get(key) is not None
        }).model_dump(mode='json', exclude_none=True)
        trace = current_execution_trace()
        value[EXECUTION_OWNER_CONTEXT_KEY] = FactoryExecutionOwner(
            **RuntimeProcessIdentity.current(),
            worker_name=(trace.worker_name if trace else None) or os.getenv('HOSTNAME') or socket.gethostname(),
            trace_id=trace.id if trace else None, trace_key=trace.trace_id if trace else None,
        ).model_dump(mode='json')
        owner = cls.current_owner()
        if owner is not None:
            value[CLEANUP_REPORT_CONTEXT_KEY] = owner
        return value

    @staticmethod
    @contextmanager
    def report_scope(detail_id=None, *, suite_id=None, case_id=None, case_type=None):
        owner = None
        if detail_id is not None:
            from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
            filters = {'id': detail_id}
            if suite_id is not None:
                filters['test_suite_id'] = suite_id
            if case_id is not None:
                filters['case_id'] = case_id
            if case_type is not None:
                filters['type'] = case_type
            row = TestCenterQuerySelector.test_suite_details().filter(**filters).values('retry').first()
            if not row or not row['retry']:
                raise DatasourceInfrastructureService.cleanup_error('平台未找到有效的报告执行记录，无法建立清理任务。请管理员检查报告明细及执行批次', detail_id=detail_id)
            owner = CleanupReportOwner(parent_case_detail_id=detail_id, parent_attempt=row['retry']).model_dump()
        token = _case_cleanup_owner.set(owner)
        try:
            yield
        finally:
            _case_cleanup_owner.reset(token)

    @staticmethod
    @DatasourceInfrastructureService.cleanup_control
    def validate_report_owner(owner, execution):
        from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
        from src.apps.test_center.enums import TestCaseTypeEnum
        if not TestCenterQuerySelector.test_suite_details().filter(
                id=owner['parent_case_detail_id'], retry=owner['parent_attempt'],
                project_product_id=execution.project_product_id,
                test_suite__project_product_id=execution.project_product_id,
                type__in=[TestCaseTypeEnum.API.value, TestCaseTypeEnum.UI.value]).exists():
            raise DatasourceInfrastructureService.cleanup_error('工厂执行与报告的产品归属或执行批次不一致，平台未执行本次清理。请管理员核对两者归属和批次', execution_id=execution.id, detail_id=owner['parent_case_detail_id'])

    @staticmethod
    def server_now():
        return DatasourceGovernorService.store().server_time()

    @staticmethod
    def wakeup_at(timestamp):
        value = datetime.fromtimestamp(timestamp, datetime_timezone.utc)
        return value if settings.USE_TZ else timezone.make_naive(value, timezone.get_default_timezone())

    @staticmethod
    @contextmanager
    def parent_wait(pulse):
        token = _parent_wait_pulse.set(pulse)
        try:
            yield
        finally:
            _parent_wait_pulse.reset(token)

    @classmethod
    @DatasourceInfrastructureService.cleanup_control
    def enqueue(cls, execution_id, *, created_by=None, controlled_retry=False, force_cleanup=True, allow_missing=True):
        # 已有入口在此之前完成 execution 数据范围及影响确认，不接受外部资源定位参数。
        owner = cls.current_owner()
        if owner is None:
            raise DatasourceInfrastructureService.cleanup_error('平台为无正式报告执行调用了调度清理入口，本次未入队。请管理员检查清理分流逻辑，无报告执行应同步清理', execution_id=execution_id)
        return ExecutorTaskService.create_cleanup_task(execution_id, created_by=created_by,
                                                       owner=owner, controlled_retry=controlled_retry,
                                                       force_cleanup=force_cleanup, allow_missing=allow_missing)

    @staticmethod
    def validate_debug_recovery(execution, owner):
        from src.apps.data_factory.enums import DataFactoryExecutionSourceEnum, DataFactoryExecutionStatusEnum
        from src.apps.data_factory.schemas.cleanup_resource import FactoryExecutionOwner
        from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation
        saved = (execution.context or {}).get(EXECUTION_OWNER_CONTEXT_KEY)
        if (execution.source_type != DataFactoryExecutionSourceEnum.TEMPLATE_DEBUG.value
                or execution.status != DataFactoryExecutionStatusEnum.SUCCESS.value
                or execution.cleanup_status not in (DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
                                                    DataFactoryCleanupStatusEnum.FAIL.value)
                or not saved or FactoryExecutionOwner.model_validate(saved) != owner
                or not DataFactoryExecutionReconciliation.owner_ended(execution)):
            raise DatasourceInfrastructureService.cleanup_error(
                '独立调试的原执行身份或结束证据不足，平台未接续清理；请核查原持有者及创建结果', execution_id=execution.id)

    @classmethod
    @transaction.atomic
    def enqueue_debug_recovery(cls, execution_id):
        from src.apps.data_factory.schemas.cleanup_resource import FactoryExecutionOwner
        execution = CleanupPersistenceService.lock_execution(execution_id)
        owner = FactoryExecutionOwner.model_validate((execution.context or {}).get(EXECUTION_OWNER_CONTEXT_KEY))
        cls.validate_debug_recovery(execution, owner)
        return ExecutorTaskService.create_cleanup_task(execution.id, force_cleanup=False, recovery_owner=owner)

    @classmethod
    @DatasourceInfrastructureService.cleanup_control
    def execute(cls, execution, *, created_by=None, controlled_retry=False, force_cleanup=True, allow_missing=True):
        from src.apps.data_factory.exceptions import DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED
        from django.db import connection
        if connection.in_atomic_block:
            raise DatasourceInfrastructureService.cleanup_error('平台数据尚未提交就开始清理，本次未执行清理。请管理员检查事务与清理调用顺序', execution_id=execution.id)
        owner = cls.current_owner()
        if owner is not None:
            cls.validate_report_owner(owner, execution)
            task = cls.enqueue(execution.id, created_by=created_by, controlled_retry=controlled_retry,
                               force_cleanup=force_cleanup, allow_missing=allow_missing)
            cls.wait(task.id, require_full_cleanup=force_cleanup)
            return task.id
        task, lease = ExecutorTaskService.begin_inline_cleanup(
            execution.id, created_by=created_by, controlled_retry=controlled_retry,
            force_cleanup=force_cleanup, allow_missing=allow_missing)
        if lease is None:
            cls.wait(task.id, require_full_cleanup=force_cleanup)
            return task.id
        if lease is not None:
            try:
                cls.run_inline(lease)
            except BaseException as error:
                from src.apps.auto_api.exceptions import TestSuiteStopped
                DatasourceInfrastructureService.capture(error, result_unknown=True)
                failure = error
                if isinstance(error, Exception) and not isinstance(error, TestSuiteStopped) and not DatasourceInfrastructureService.current():
                    failure = DatasourceInfrastructureService.internal_cleanup_error(error, 'synchronous_cleanup', execution_id=execution.id)
                progress = dict(lease.progress)
                progress['infrastructure_issues'] = [issue.model_dump(mode='json')
                                                    for issue in DatasourceInfrastructureService.current()]
                try:
                    with CleanupPersistenceService.lease(lease):
                        message = getattr(failure, 'msg', DATA_FACTORY_CLEANUP_INTERRUPTED.message)
                        DataFactoryCleanup.mark_execution_failed(execution, message)
                        ExecutorTaskService.finish_cleanup_step(lease, progress,
                                                               error=message)
                except Exception:
                    log.system.exception(f'同步清理失败状态持久化未完成，execution_id={execution.id}，需恢复核查')
                if failure is not error:
                    raise failure from error
                raise
        row = TaskCenterQuerySelector.executor_tasks().filter(id=task.id).values('status', 'error_message', 'progress_data').first()
        if not row:
            raise DatasourceInfrastructureService.cleanup_error('未找到对应的清理任务，平台无法继续等待清理结果。请管理员排查任务记录', task_id=task.id)
        if row['status'] not in ExecutorTaskStatusEnum.terminal_values():
            cls.wait(task.id, require_full_cleanup=force_cleanup)
            return task.id
        if row['status'] != ExecutorTaskStatusEnum.SUCCESS.value:
            cls.require_failure_evidence(row)
            raise DataFactoryError(DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED,
                                   value=(row.get('error_message') or f'清理任务 {task.id} 未通过验证，请在数据工厂执行记录中查看失败资源和验证明细',))
        cls.verify_complete(execution.id, require_full_cleanup=force_cleanup)
        return task.id

    @classmethod
    def run_inline(cls, lease):
        token = _inline_observation_items.set({})
        try:
            with CleanupPersistenceService.lease(lease):
                cls.run_inline_steps(lease)
        finally:
            _inline_observation_items.reset(token)

    @classmethod
    def run_inline_steps(cls, lease):
        while True:
            next_at = cls.run_claimed(lease, inline=True)
            if next_at is None:
                break
            # 等待期间也维护原租约；不读取队列、不依赖 scheduler 在线。
            while True:
                CleanupPersistenceService.check()
                remaining = next_at - cls.server_now().timestamp()
                if remaining <= 0:
                    break
                pulse = _parent_wait_pulse.get()
                if pulse is not None:
                    pulse()
                sleep(min(remaining, 1))

    @staticmethod
    def set_owner(detail_id, attempt):
        return _case_cleanup_owner.set({'parent_case_detail_id': detail_id, 'parent_attempt': attempt})

    @staticmethod
    def reset_owner(token):
        _case_cleanup_owner.reset(token)

    @staticmethod
    @transaction.atomic
    def record_wait_failure(execution_id):
        execution = DataFactoryExecution.objects.select_for_update().get(id=execution_id)
        if execution.cleanup_status not in (DataFactoryCleanupStatusEnum.SUCCESS.value,
                                            DataFactoryCleanupStatusEnum.FAIL.value):
            # Case 的等待失败不能取消持久清理，但必须立即保留失败责任和待办。
            DataFactoryCleanup.mark_execution_failed(
                execution, DATA_FACTORY_CLEANUP_INTERRUPTED.message, mark_pending_items=False)

    @classmethod
    @DatasourceInfrastructureService.cleanup_control
    def wait(cls, task_id, *, require_full_cleanup=True, sql_only=False):
        from src.apps.task_center.services.execution.cooperative_executor import wait_until
        from src.apps.data_factory.exceptions import DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED
        from django.db import connection
        if connection.in_atomic_block:
            raise DatasourceInfrastructureService.cleanup_error('平台在尚未提交的事务中等待清理任务。请管理员检查事务与调度调用顺序', task_id=task_id)
        result = {}
        started = monotonic()
        next_log = started + 30
        pulse = _parent_wait_pulse.get()
        owner = _case_cleanup_owner.get()
        log.system.info(
            f'event=factory_cleanup_wait_started task_id={task_id} '
            f'detail_id={(owner or {}).get("parent_case_detail_id")} '
            f'attempt={(owner or {}).get("parent_attempt")} thread_id={threading.get_ident()} '
            f'phase={"sql" if sql_only else "complete"}')

        def ready():
            nonlocal next_log
            if pulse is not None:
                pulse()
            if owner:
                from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
                from mangotools.enums import TaskEnum
                valid = TestCenterQuerySelector.test_suite_details().filter(
                    id=owner['parent_case_detail_id'], retry=owner['parent_attempt'], status=TaskEnum.PROCEED.value,
                ).exists()
                if not valid:
                    raise DatasourceInfrastructureService.cleanup_error('当前Case执行已结束或已开始新一轮执行，旧步骤不再继续；原清理任务仍保留，请查看其最新清理状态', task_id=task_id, detail_id=owner['parent_case_detail_id'])
            task = TaskCenterQuerySelector.executor_tasks().filter(id=task_id).values(
                'status', 'error_message', 'business_id', 'progress_data').first()
            if not task:
                raise DatasourceInfrastructureService.cleanup_error('未找到对应的清理任务，平台无法继续等待清理结果。请管理员排查任务记录', task_id=task_id)
            result.update(task)
            now = monotonic()
            if now >= next_log:
                log.system.warning(
                    f'event=factory_cleanup_long_wait task_id={task_id} execution_id={task["business_id"]} '
                    f'detail_id={(owner or {}).get("parent_case_detail_id")} '
                    f'attempt={(owner or {}).get("parent_attempt")} thread_id={threading.get_ident()} '
                    f'phase={"sql" if sql_only else "complete"} elapsed_ms={(now - started) * 1000:.2f} '
                    f'status={task["status"]} sql_done={(task.get("progress_data") or {}).get("sql_done") is True}')
                next_log = now + 30
            return (task['status'] in ExecutorTaskStatusEnum.terminal_values()
                    or (sql_only and (task.get('progress_data') or {}).get('sql_done') is True))

        # Case 等待最终清理结果；排队时长不冒充 SQL/ES 校验超时。
        # 真正清理的时限仍由消费者 run_claimed 与 ES 观察窗口负责。
        if not ready():
            wait_until(ready, float('inf'))
        log.system.info(
            f'event=factory_cleanup_wait_finished task_id={task_id} execution_id={result["business_id"]} '
            f'detail_id={(owner or {}).get("parent_case_detail_id")} '
            f'attempt={(owner or {}).get("parent_attempt")} thread_id={threading.get_ident()} '
            f'phase={"sql" if sql_only else "complete"} elapsed_ms={(monotonic() - started) * 1000:.2f} '
            f'status={result["status"]}')
        if sql_only and result['status'] not in ExecutorTaskStatusEnum.terminal_values():
            return
        if result['status'] != ExecutorTaskStatusEnum.SUCCESS.value:
            cls.require_failure_evidence(result)
            raise DataFactoryError(DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED,
                                   value=(result.get('error_message') or f'清理任务 {task_id} 未通过验证，请在数据工厂执行记录中查看失败资源和验证明细',))
        cls.verify_complete(result['business_id'], require_full_cleanup=require_full_cleanup)

    @staticmethod
    @DatasourceInfrastructureService.cleanup_control
    def verify_complete(execution_id, *, require_full_cleanup):
        execution = DataFactoryExecution.objects.get(id=execution_id)
        complete = execution.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value
        if execution.cleanup_status == DataFactoryCleanupStatusEnum.SKIPPED.value:
            complete = (not require_full_cleanup
                        or not DataFactoryExecutionItem.objects.filter(execution=execution).exists())
        if not complete:
            raise DatasourceInfrastructureService.cleanup_error('清理任务已结束，但执行记录未提供完整的清理成功验证。请管理员检查任务结果和清理明细，不能判定通过', execution_id=execution_id)
        if require_full_cleanup and DataFactoryExecutionItem.objects.filter(execution=execution).exclude(
                cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).exists():
            remaining = DataFactoryExecutionItem.objects.filter(execution=execution).exclude(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).count()
            raise DatasourceInfrastructureService.cleanup_error(f'清理任务标记为成功，但仍有 {remaining} 项未验证清理成功。请管理员检查清理明细，本次不能判定通过', execution_id=execution_id)
        if require_full_cleanup:
            from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
            for item in DataFactoryExecutionItem.objects.filter(execution=execution):
                state = DataFactoryCleanupResourceService.state(item)
                if DataFactoryCleanupResourceService.pending_compensations(state):
                    raise DatasourceInfrastructureService.cleanup_error('本次ES补偿尚无匹配授权的完整清理验证，不能沿用旧成功结果。请查看指定资源的补偿任务及观察检查点', execution_id=execution_id, execution_item_id=item.id)
                DataFactoryCleanupResourceService.resolve_verified(state)

    @classmethod
    def run_next(cls, *, observations_only=False):
        if not observations_only:
            lease = ExecutorTaskService.claim_cleanup_task()
            if lease is None:
                return False
            cls.run_claimed(lease)
            return True
        capacity = min(ES_CLEANUP_PROBE_WORKERS, DatasourceGovernorService.policy().pool_size)
        leases = []
        for _ in range(capacity):
            try:
                lease = ExecutorTaskService.claim_cleanup_task(observations_only=True)
            except Exception:
                if not leases:
                    raise
                log.system.exception('领取ES观察任务中断，已领取任务仍按原租约处理')
                break
            if lease is None:
                break
            leases.append(lease)
        if not leases:
            return False
        if len(leases) == 1:
            cls.run_claimed(leases[0])
            return True
        log.system.debug('event=factory_cleanup_observation_dispatch tasks=%s task_ids=%s workers=%s probe_workers_per_task=%s',
                         len(leases), [lease.task_id for lease in leases], len(leases), max(1, capacity // len(leases)))

        def observe(lease):
            from django.db import close_old_connections, connections
            token = _probe_worker_budget.set(max(1, capacity // len(leases)))
            try:
                close_old_connections()
                with DatasourceWaitService.owner(None):
                    cls.run_claimed(lease)
            finally:
                _probe_worker_budget.reset(token)
                connections.close_all()

        # 独立任务使用独立租约；嵌套资源采样共享此批预算，不能变成 capacity 的平方。
        with ThreadPoolExecutor(max_workers=len(leases), thread_name_prefix='factory-es-observe') as executor:
            list(executor.map(observe, leases))
        return True

    @classmethod
    def run_claimed(cls, lease, *, inline=False):
        with DatasourceInfrastructureService.scope():
            try:
                return cls.run_claimed_step(lease, inline=inline)
            except Exception as error:
                DatasourceInfrastructureService.capture(error, result_unknown=True)
                failure = error
                if not DatasourceInfrastructureService.current():
                    failure = DatasourceInfrastructureService.internal_cleanup_error(error, 'run_claimed', task_id=lease.task_id)
                progress = dict(lease.progress) if isinstance(lease.progress, dict) else {}
                progress['infrastructure_issues'] = [issue.model_dump(mode='json')
                                                    for issue in DatasourceInfrastructureService.current()]
                # 写入仍校验原 token；控制库不可用时向外抛出，保留任务等待恢复，不猜测成功。
                message = getattr(failure, 'msg', None) or DatasourceInfrastructureService.summary()
                ExecutorTaskService.finish_cleanup_step(lease, progress,
                    error=f'清理任务 {lease.task_id} 未完成：{message}')
                return None

    @staticmethod
    def restore_infrastructure(raw):
        try:
            progress = CleanupTaskProgress.model_validate(raw or {}, strict=True)
        except ValidationError as error:
            failure = DatasourceInfrastructureService.cleanup_error('清理任务的故障结果记录格式不正确，平台无法读取最终结果。请管理员检查任务进度快照')
            raise failure from error
        DatasourceInfrastructureService.absorb(progress.infrastructure_issues)
        return progress

    @classmethod
    def require_failure_evidence(cls, row):
        progress = cls.restore_infrastructure(row.get('progress_data'))
        if row['status'] != ExecutorTaskStatusEnum.FAILED.value or (
                not progress.verification_failed and not progress.infrastructure_issues):
            reason = ('清理任务未以完整终态结束' if row['status'] != ExecutorTaskStatusEnum.FAILED.value else '清理任务标记失败，但缺少验证失败明细或平台异常记录')
            raise DatasourceInfrastructureService.cleanup_error(reason + '，当前无法确认清理结果。请管理员检查清理任务和进度记录', execution_id=row.get('business_id'))

    @classmethod
    def run_claimed_step(cls, lease, *, inline=False):
        try:
            progress = CleanupTaskProgress.model_validate(lease.progress, strict=True).model_dump(mode='json', exclude_none=True)
            payload = CleanupTaskPayload.model_validate(lease.payload, strict=True)
        except ValidationError:
            error = DataFactoryError(DATA_FACTORY_CLEANUP_INTERRUPTED)
            error.msg = f'清理任务 {lease.task_id} 保存的执行快照格式不正确，平台未继续执行。请管理员检查任务快照，勿直接重放删除'
            DatasourceInfrastructureService.capture(error)
            evidence = {'infrastructure_issues': [issue.model_dump(mode='json')
                                                 for issue in DatasourceInfrastructureService.current()]}
            ExecutorTaskService.finish_cleanup_step(lease, evidence, error=error.msg)
            return None
        execution_id = payload.execution_id
        progress.pop('claim_token', None)
        now = cls.server_now()
        progress.setdefault('started_at', now.timestamp())
        measured_at = monotonic()
        wait_started = DatasourceWaitService.elapsed()
        parallel_wait = 0.0
        # 旧任务只有总处理时间，按原持久阶段归入对应预算，不丢弃已有耗时。
        if not progress['sql_seconds'] and not progress['es_seconds'] and progress['active_seconds']:
            progress['es_seconds' if progress.get('sql_done') else 'sql_seconds'] = progress['active_seconds']
        phase = 'es_seconds' if progress.get('sql_done') else 'sql_seconds'

        def account(*, enforce=True):
            nonlocal measured_at, wait_started, parallel_wait
            current, waited = monotonic(), DatasourceWaitService.elapsed()
            duration = max(0, current - measured_at - max(0, waited - wait_started) - parallel_wait)
            parallel_wait = 0.0
            progress['active_seconds'] += duration
            progress[phase] += duration
            measured_at, wait_started = current, waited
            lease.progress = progress
            limit = DatasourceGovernorService.policy().cleanup_completion_seconds
            if enforce and progress[phase] > limit:
                remaining = DataFactoryExecutionItem.objects.filter(execution_id=execution_id).exclude(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).count()
                error = DataFactoryError(DATA_FACTORY_CLEANUP_TIMEOUT)
                error.msg += (f'。阶段：{"SQL清理" if phase == "sql_seconds" else "ES清理与验证"}，'
                              f'本阶段实际处理 {progress[phase]:.2f} 秒，上限 {limit} 秒；'
                              f'SQL累计 {progress["sql_seconds"]:.2f} 秒，ES累计 {progress["es_seconds"]:.2f} 秒'
                              f'（不含资源排队和任务调度等待），未确认完成 {remaining} 项')
                raise DatasourceInfrastructureService.annotate(error, execution_id=execution_id, task_id=lease.task_id)

        with CleanupPersistenceService.lease(lease):
            try:
                CleanupPersistenceService.check()
                if (payload.mode == DataFactoryCleanupModeEnum.SYNCHRONOUS) != inline:
                    raise DatasourceInfrastructureService.cleanup_error('清理任务的同步/调度执行方式与当前执行进程不匹配，平台未执行本次清理。请管理员检查清理分流和任务领取逻辑', execution_id=execution_id, task_id=lease.task_id)
                if not inline and payload.recovery_owner is not None:
                    if payload.parent_case_detail_id is not None or payload.parent_attempt is not None or payload.force_cleanup:
                        raise DatasourceInfrastructureService.cleanup_error('调试恢复任务混入报告归属或强制清理配置，平台未执行清理', execution_id=execution_id)
                    cls.validate_debug_recovery(DataFactoryExecution.objects.get(id=execution_id), payload.recovery_owner)
                elif not inline:
                    owner = CleanupReportOwner.model_validate({
                        'parent_case_detail_id': payload.parent_case_detail_id,
                        'parent_attempt': payload.parent_attempt}, strict=True).model_dump()
                    cls.validate_report_owner(owner, DataFactoryExecution.objects.get(id=execution_id))
                account()
                if not progress.get('sql_done'):
                    if lease.recovered:
                        # 领取者失联时 SQL 可能仍在执行；不把失联当作未执行而重放。
                        raise DataFactoryError(DATA_FACTORY_CLEANUP_INTERRUPTED)
                    result = DataFactoryCleanup.cleanup_execution(
                        execution_id, force_cleanup=payload.force_cleanup,
                        allow_missing=payload.allow_missing, defer_resources=True)
                    if result.get('fail'):
                        account()
                        progress['verification_failed'] = not bool(DatasourceInfrastructureService.current())
                        progress['infrastructure_issues'] = [issue.model_dump(mode='json')
                                                            for issue in DatasourceInfrastructureService.current()]
                        reasons = list(DataFactoryExecutionItem.objects.filter(execution_id=execution_id, cleanup_error__isnull=False).exclude(cleanup_error='').values_list('cleanup_error', flat=True)[:3])
                        message = '数据库清理未通过验证：' + '；'.join(reasons) if reasons else '数据库清理返回失败，但未提供具体失败原因。请管理员检查工厂执行记录和清理快照'
                        ExecutorTaskService.finish_cleanup_step(lease, progress, error=message)
                        return None
                    progress['sql_done'] = True
                    account()
                    phase = 'es_seconds'
                items = cls.observation_items(execution_id, lease, inline=inline)
                skipped = False
                pending = []
                observed_at = cls.server_now().timestamp()
                eligible = []
                for item in items:
                    if item.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value:
                        continue
                    if not payload.force_cleanup and item.cleanup_strategy in (
                            DataFactoryCleanupStrategyEnum.NONE.value, DataFactoryCleanupStrategyEnum.MANUAL.value):
                        skipped = True
                        continue
                    eligible.append(item)
                # 未进入工作集的资源尚不开始观察窗口。不能让整个大批次同时开始计时，
                # 再每轮只服务其中一小部分，导致其他资源被平台自身调度反复重置。
                workers = min(_probe_worker_budget.get(), DatasourceGovernorService.policy().pool_size)
                capacity = min(ES_CLEANUP_PROBE_BATCH_SIZE, workers * ES_CLEANUP_RESOURCES_PER_WORKER)
                active_items = eligible[:capacity]
                has_more = len(eligible) > len(active_items)
                for item in active_items:
                    next_at = DataFactoryCleanupResourceService.initialize_observation(
                        item, generation=lease.generation, task_id=lease.task_id, observed_at=observed_at)
                    if next_at is None:
                        DataFactoryCleanup.mark_success(item)
                    else:
                        pending.append((item, next_at))
                if pending:
                    pending, parallel_wait = cls.probe_observations(pending, lease)
                    account()
                    if pending:
                        next_at = min(at for value, at in pending)
                        kwargs = {'inline': True} if inline else {}
                        accepted = ExecutorTaskService.finish_cleanup_step(
                            lease, progress, next_at=cls.wakeup_at(next_at), **kwargs)
                        if accepted:
                            lease.progress = progress
                            return next_at
                        return None
                if has_more:
                    account()
                    next_at = cls.server_now().timestamp()
                    kwargs = {'inline': True} if inline else {}
                    if ExecutorTaskService.finish_cleanup_step(lease, progress,
                            next_at=cls.wakeup_at(next_at), **kwargs):
                        lease.progress = progress
                        return next_at
                    return None
                account()
                cls.finish_verified_execution(execution_id, lease, progress, skipped=skipped)
            except Exception as error:
                account(enforce=False)
                DatasourceInfrastructureService.capture(error, result_unknown=True)
                if not isinstance(error, DataFactoryError) and not DatasourceInfrastructureService.current():
                    error = DatasourceInfrastructureService.internal_cleanup_error(error, 'cleanup_dispatch', execution_id=execution_id, task_id=lease.task_id)
                progress['verification_failed'] = not bool(DatasourceInfrastructureService.current())
                progress['infrastructure_issues'] = [issue.model_dump(mode='json')
                                                    for issue in DatasourceInfrastructureService.current()]
                message = error.msg if isinstance(error, DataFactoryError) else (
                    f'工厂执行 {execution_id} 的清理任务 {lease.task_id} 未完成：' + DatasourceInfrastructureService.summary())
                try:
                    execution = DataFactoryExecution.objects.filter(id=execution_id).first()
                    if execution is not None:
                        DataFactoryCleanup.mark_execution_failed(execution, message)
                    ExecutorTaskService.finish_cleanup_step(lease, progress, error=message)
                except DataFactoryError:
                    # 租约被回收后旧执行者不能改写失败/成功状态。
                    pass
        return None

    @classmethod
    def finish_verified_execution(cls, execution_id, lease, progress, *, skipped):
        from django.db import OperationalError, InterfaceError
        from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
        for attempt in range(3):
            try:
                return cls.persist_verified_execution(execution_id, lease, progress, skipped=skipped,
                                                     accept_completed=attempt > 0)
            except (OperationalError, InterfaceError) as error:
                number = DataSourceErrorService.server_error_number(error)
                connection = transaction.get_connection()
                if (attempt == 2 or connection.in_atomic_block
                        or not (number in (1205, 1213, 2006, 2013, 2055)
                                or isinstance(error, InterfaceError) and number == 0)):
                    raise
                if number not in (1205, 1213):
                    connection.close()
                log.system.warning('event=factory_cleanup_finalization_retry execution_id=%s task_id=%s '
                    'attempt=%s driver_error_number=%s action=verify_lease_and_persist_only',
                    execution_id, lease.task_id, attempt + 1, number)

    @staticmethod
    def persist_verified_execution(execution_id, lease, progress, *, skipped, accept_completed=False):
        # 执行与任务终态同一事务，先锁执行再锁任务，与补偿授权/任务创建使用同一顺序。
        # 只保存已验证结果；控制库失败由持久明细对账，不在此重放任何外部操作。
        with transaction.atomic():
            execution = CleanupPersistenceService.lock_execution(execution_id)
            completed = accept_completed and ExecutorTaskService.cleanup_success_matches_lease(lease, execution_id)
            if not completed:
                CleanupPersistenceService.check()
            items = list(DataFactoryExecutionItem.objects.select_for_update().filter(execution_id=execution_id))
            verified_items = [item for item in items if not skipped or getattr(item, 'cleanup_strategy',
                DataFactoryCleanupStrategyEnum.EXECUTION_END.value) == DataFactoryCleanupStrategyEnum.EXECUTION_END.value]
            if verified_items and not DataFactoryCleanup.cleanup_is_verified(verified_items):
                raise DatasourceInfrastructureService.cleanup_error(
                    '清理结束时持久明细缺少完整成功证据，平台未写入成功状态，请核查资源验证记录',
                    execution_id=execution_id, task_id=lease.task_id)
            expected_status = (DataFactoryCleanupStatusEnum.SUCCESS.value if items and not skipped
                               else DataFactoryCleanupStatusEnum.SKIPPED.value)
            if completed:
                if execution.cleanup_status != expected_status:
                    raise DatasourceInfrastructureService.cleanup_error(
                        '任务成功状态与工厂执行状态不一致，请按持久验证证据对账，平台未重放清理',
                        execution_id=execution_id, task_id=lease.task_id)
                return
            execution.cleanup_status = expected_status
            execution.cleanup_time = timezone.now()
            DataFactoryCleanup.clear_resolved_cleanup_error(execution)
            CleanupPersistenceService.save(execution, ['cleanup_status', 'cleanup_time', 'error_message', 'update_time'])
            if not ExecutorTaskService.finish_cleanup_step(lease, progress, success=True):
                raise DatasourceInfrastructureService.cleanup_error(
                    '清理任务租约已改变，未保存本次成功终态，请核查当前执行持有者',
                    execution_id=execution_id, task_id=lease.task_id)
            transaction.on_commit(lambda: DataFactoryCleanup.sync_workbench_todo(execution))
