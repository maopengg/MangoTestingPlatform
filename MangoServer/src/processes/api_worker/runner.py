import os
import socket
from concurrent.futures import FIRST_COMPLETED, wait

import time
from django.db import connection, DatabaseError

from src.apps.auto_api.services.execution.cases.test_case import TestCase
from src.apps.system.enums import ExecutorTaskTypeEnum, RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.services.execution.claim import ApiTaskClaimService
from src.common.decorators.retry import async_task_db_connection
from src.common.decorators.system_error import system_error_guard
from src.common.logging import log
from src.processes.api_worker.db_context import (
    WorkerDbContextRegistry,
    set_current_worker_db_context,
)


class ApiWorkerRunner:
    def __init__(
            self,
            worker_name: str | None = None,
            thread_pool_size: int = 5,
            lease_seconds: int | None = None,
            poll_interval: int = 3,
            db_idle_seconds: int = 1800,
            config_refresh_interval: int = 10,
    ):
        self.worker_name = worker_name or socket.gethostname()
        self.thread_pool_size = SystemConfigService.get_api_worker_thread_pool_size(thread_pool_size)
        self.executor_size = self.thread_pool_size
        self.lease_seconds_override = lease_seconds
        self.lease_seconds = (
            lease_seconds
            if lease_seconds is not None
            else SystemConfigService.get_executor_execution_timeout_seconds(
                ExecutorTaskTypeEnum.API_EXECUTION.value,
                default_seconds=60 * 60,
            )
        )
        self.poll_interval = poll_interval
        self.config_refresh_interval = config_refresh_interval
        self.last_config_refresh_at = 0
        self.last_recovery_at = 0
        self.running = True
        self.db_context_registry = WorkerDbContextRegistry(idle_seconds=db_idle_seconds)
        self.executor = self.create_executor(self.executor_size)

    @system_error_guard(
        source=SystemErrorEventSource.API_WORKER,
        request_path='run_api_worker',
        service_name=RuntimeServiceName.API_WORKER,
    )
    def run_forever(self):
        futures = {}
        try:
            from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
            # 构造阶段已经启动非守护线程；启动校验失败也必须进入同一条资源回收路径。
            DatasourceGovernorService.policy()
            log.api.info(f'api-worker 启动：worker={self.worker_name}, thread_pool_size={self.thread_pool_size}')
            while self.running:
                try:
                    self.refresh_thread_pool_size(futures)
                    self.report_heartbeat(futures)
                    if time.monotonic() - self.last_recovery_at >= 15:
                        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
                        ApiWorkerRecoveryService.recover()
                        self.last_recovery_at = time.monotonic()
                except DatabaseError:
                    # 控制库故障只暂停领取，不重启整批已在执行的业务请求。
                    log.api.warning('event=api_worker_control_unavailable action=pause_claim')
                    connection.close()
                    time.sleep(self.poll_interval)
                    continue
                while self.running and self.can_claim(futures):
                    try:
                        case_model = self.claim()
                    except DatabaseError:
                        log.api.warning('event=api_worker_control_unavailable action=pause_claim')
                        connection.close()
                        break
                    if not case_model:
                        self._next_claim_at = time.monotonic() + self.poll_interval
                        break
                    futures[self.executor.submit(self.execute, case_model)] = case_model
                if futures:
                    # 协作等待不放大 Case 领取数；短轮询及时收口已完成 Future。
                    done, _ = wait(futures, timeout=min(self.poll_interval, 0.1), return_when=FIRST_COMPLETED)
                    self.observe_completions(done)
                    if done and not self.settle_finished(futures, done):
                        # 已完成 Future 的 wait 会立即返回；控制库异常时必须退避，不能空转轰击。
                        time.sleep(self.poll_interval)
                else:
                    time.sleep(self.poll_interval)
        finally:
            # 排空时继续心跳并收口已结束但未落结果的执行，不依赖一小时超时扫描。
            while futures:
                done, _ = wait(futures, timeout=self.poll_interval, return_when=FIRST_COMPLETED)
                try:
                    self.report_heartbeat(futures)
                    self.observe_completions(done)
                    if done and not self.settle_finished(futures, done):
                        time.sleep(self.poll_interval)
                except DatabaseError:
                    connection.close()
                    time.sleep(self.poll_interval)
            self.executor.shutdown(wait=True)
            self.db_context_registry.close_all()
            from src.apps.data_factory.services.pool.datasource_pool import DatasourcePoolRegistry
            from src.apps.data_factory.services.pool.protocol_pool import ProtocolPoolRegistry
            DatasourcePoolRegistry.close_all()
            ProtocolPoolRegistry.close_all()

    @staticmethod
    def settle_finished(futures, done):
        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
        settled = 0
        for future in done:
            case_model = futures[future]
            code_bug = False
            result_expected = False
            try:
                future.result()
            except Exception as error:
                from src.common.exceptions import MangoServerError
                from src.apps.test_center.exceptions import ExecutionResultStorageError
                from src.apps.test_center.services.reporting.test_suite.recovery import ReportRecoveryService
                code_bug = ReportRecoveryService.is_confirmed_code_bug(error)
                result_expected = not code_bug and (isinstance(error, ExecutionResultStorageError)
                                                   or not isinstance(error, MangoServerError))
                if not getattr(future, '_mango_error_logged', False):
                    log.api.error('event=api_worker_execution_incomplete detail_id=%s exception_type=%s',
                                  case_model.test_suite_details, type(error).__name__)
                    future._mango_error_logged = True
            try:
                recovery_options = {'code_bug': code_bug}
                if result_expected:
                    recovery_options['result_expected'] = True
                ApiWorkerRecoveryService.finish_unreported(case_model.test_suite_details, case_model.attempt, **recovery_options)
            except DatabaseError:
                # 保留完成凭据，下轮仅重试结果收口，不再次执行 Case。
                connection.close()
                continue
            futures.pop(future)
            settled += 1
        return settled

    def stop(self):
        # SIGTERM 先停止领取，允许在途请求与严格清理继续完成。
        self.running = False

    def create_executor(self, thread_pool_size: int):
        from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor
        return CooperativeCaseExecutor(max_workers=thread_pool_size, thread_name_prefix=self.worker_name)

    def current_claim_limit(self):
        return min(self.thread_pool_size, self.executor_size)

    def can_claim(self, futures):
        # 驻留 Case 也计入 Worker 配置容量，不再用数据源等待上限扩容预取。
        if time.monotonic() < getattr(self, '_next_claim_at', 0):
            return False
        return len(futures) < self.current_claim_limit()

    def refresh_thread_pool_size(self, futures: dict):
        now = time.monotonic()
        if now - self.last_config_refresh_at < self.config_refresh_interval:
            return
        self.last_config_refresh_at = now
        configured_size = SystemConfigService.get_api_worker_thread_pool_size(self.thread_pool_size)
        if self.lease_seconds_override is None:
            configured_lease_seconds = (
                SystemConfigService.get_executor_execution_timeout_seconds(
                    ExecutorTaskTypeEnum.API_EXECUTION.value,
                    default_seconds=60 * 60,
                )
            )
            if configured_lease_seconds != self.lease_seconds:
                log.api.info(
                    f'api-worker 最大执行时间配置变更：worker={self.worker_name}, '
                    f'old={self.lease_seconds}, new={configured_lease_seconds}'
                )
                self.lease_seconds = configured_lease_seconds
        if configured_size != self.thread_pool_size:
            log.api.info(
                f'api-worker 线程池配置变更：worker={self.worker_name}, '
                f'old={self.thread_pool_size}, new={configured_size}'
            )
            self.thread_pool_size = configured_size
        if self.executor_size == self.thread_pool_size or futures:
            return
        old_executor = self.executor
        self.executor = self.create_executor(self.thread_pool_size)
        self.executor_size = self.thread_pool_size
        old_executor.shutdown(wait=True)
        log.api.info(f'api-worker 线程池已重建：worker={self.worker_name}, thread_pool_size={self.executor_size}')

    def report_heartbeat(self, futures: dict):
        from src.apps.data_factory.services.pool.pool_maintenance import DatasourcePoolMaintenance
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        ServiceHeartbeatService.beat_if_due(
            self,
            RuntimeServiceName.API_WORKER,
            instance_name=self.worker_name,
            metadata={
                **RuntimeProcessIdentity.current(),
                'pod_uid': os.getenv('POD_UID'),
                'execution_loop_alive': self.running,
                'executor_threads_alive': all(thread.is_alive() for thread in self.executor.threads),
                'thread_pool_size': self.thread_pool_size,
                'executor_size': self.executor_size,
                'running_count': len(futures),
                'resource_waiting_count': sum(bool(getattr(future, '_mango_resource_parked', False))
                                              for future in futures),
                'claim_limit': self.current_claim_limit(),
                'lease_seconds': self.lease_seconds,
                'poll_interval': self.poll_interval,
                'db_idle_seconds': self.db_context_registry.idle_seconds,
                'datasource_maintenance_healthy': DatasourcePoolMaintenance.healthy(),
                **self.execution_progress(futures),
            },
        )

    def observe_completions(self, finished, *, now=None):
        previous = getattr(self, '_observed_finished', set())
        if finished - previous:
            self._last_completion_at = time.monotonic() if now is None else now
            if getattr(self, '_stalled_logged_at', None) is not None:
                log.api.info('event=api_worker_execution_progress_restored worker=%s', self.worker_name)
                self._stalled_logged_at = None
        self._observed_finished = previous | finished

    def execution_progress(self, futures):
        now = time.monotonic()
        finished = {future for future in futures if future.done()}
        # wait 后的完成项会在下一次心跳前被移除，必须在收口前记录，不能只扫描当前 Future。
        self.observe_completions(finished, now=now)
        self._observed_finished = finished
        if not futures or not hasattr(self, '_last_completion_at'):
            self._last_completion_at = now
            if getattr(self, '_stalled_logged_at', None) is not None:
                log.api.info('event=api_worker_execution_progress_restored worker=%s', self.worker_name)
                self._stalled_logged_at = None
        completion_elapsed = max(0, now - self._last_completion_at)
        if not futures:
            self._last_activity_at = now
            self._progress_evidence_available = True
        if futures and completion_elapsed >= 60 and now - getattr(self, '_activity_checked_at', float('-inf')) >= 15:
            from datetime import timedelta
            from django.utils import timezone
            from src.apps.data_factory.services.reporting.execution_progress import DatasourceExecutionProgressService
            wall_now = timezone.now()
            activities = DatasourceExecutionProgressService.for_attempts(
                {item.test_suite_details: item.attempt for item in futures.values()},
                wall_now - timedelta(seconds=60))
            self._progress_evidence_available = activities is not None
            if activities:
                wall_stamp = (timezone.make_aware(wall_now, timezone.get_default_timezone())
                              if timezone.is_naive(wall_now) else wall_now).timestamp()
                age = max(0, wall_stamp - max(activities.values()))
                self._last_activity_at = max(getattr(self, '_last_activity_at', 0), now - age)
            self._activity_checked_at = now
        elapsed = max(0, now - max(self._last_completion_at, getattr(self, '_last_activity_at', 0)))
        evidence_available = getattr(self, '_progress_evidence_available', True)
        logged = getattr(self, '_stalled_logged_at', None)
        if evidence_available and elapsed < 60 and logged is not None:
            log.api.info('event=api_worker_execution_progress_restored worker=%s', self.worker_name)
            self._stalled_logged_at = None
        if futures and evidence_available and elapsed >= 60 and (logged is None or now - logged >= 60):
            contexts = [{'report_id': item.test_suite, 'detail_id': item.test_suite_details,
                         'case_id': item.case_id, 'attempt': item.attempt}
                        for item in list(futures.values())[:10]]
            log.api.warning('event=api_worker_no_progress worker=%s running_count=%s '
                'no_completion_seconds=%.2f no_progress_seconds=%.2f executions=%s '
                'action=inspect_datasource_wait_and_case_progress',
                self.worker_name, len(futures), completion_elapsed, elapsed, contexts)
            self._stalled_logged_at = now
        if evidence_available and now - getattr(self, '_health_observed_at', float('-inf')) >= 15:
            from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService
            from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
            process = RuntimeProcessIdentity.current()['process_token']
            items = list(futures.values())[:10]
            DatasourceHealthIncidentService.safe_observe(f'api-worker:{self.worker_name}:{process}',
                worker=True, active=bool(futures and elapsed >= 60), metrics={
                    'no_completion_seconds': completion_elapsed, 'no_progress_seconds': elapsed,
                    'waiting_count': sum(bool(getattr(future, '_mango_resource_parked', False)) for future in futures),
                    'report_ids': list(dict.fromkeys(item.test_suite for item in items)),
                    'detail_ids': [item.test_suite_details for item in items],
                    'case_ids': [item.case_id for item in items]})
            self._health_observed_at = now
        return {'no_completion_seconds': round(completion_elapsed, 2),
                'no_progress_seconds': round(elapsed, 2), 'completed_waiting_settlement': len(finished)}

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def claim(self):
        from src.apps.data_factory.exceptions import DataFactoryError
        try:
            from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
            return ApiTaskClaimService.claim(lease_seconds=self.lease_seconds, worker_owner={
                'worker_name': self.worker_name, **RuntimeProcessIdentity.current()})
        except DataFactoryError as error:
            log.api.warning('event=api_worker_capacity_unavailable code=%s action=pause_claim', error.code)
            return None

    @system_error_guard(
        source=SystemErrorEventSource.API_WORKER,
        request_path='execute_api_case',
        service_name=RuntimeServiceName.API_WORKER,
    )
    def execute(self, case_model):
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
        db_context = self.db_context_registry.current()
        set_current_worker_db_context(db_context)
        cleanup_owner = DataFactoryCleanupScheduleService.set_owner(case_model.test_suite_details, case_model.attempt)
        try:
            connection.close()
            db_context.close_idle()
            test_case = TestCase(
                user_id=case_model.user_id,
                test_env=case_model.test_env,
                case_id=case_model.case_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
                revision_id=case_model.case_revision_id,
                release_id=case_model.case_release_id,
                config_checksum=case_model.config_checksum,
                db_context=db_context,
            )
            from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
            from src.apps.auto_api.exceptions import TestSuiteStopped
            last_pulse = 0

            def pulse():
                nonlocal last_pulse
                now = time.monotonic()
                if now - last_pulse >= 1:
                    if not ApiTaskClaimService.renew_wait(case_model, self.lease_seconds):
                        raise TestSuiteStopped
                    last_pulse = now

            with DatasourceWaitService.owner(pulse), DataFactoryCleanupScheduleService.parent_wait(pulse):
                return test_case.test_case(parametrize=case_model.parametrize)
        finally:
            try:
                connection.close()
            except Exception:
                pass
            try:
                self.db_context_registry.release(db_context)
            finally:
                set_current_worker_db_context(None)
                DataFactoryCleanupScheduleService.reset_owner(cleanup_owner)
