import socket
from concurrent.futures import FIRST_COMPLETED, wait

import time
from django.db import connection, DatabaseError

from src.apps.auto_api.services.test_case.test_case import TestCase
from src.apps.system.enums import ExecutorTaskTypeEnum, RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.apps.system.services.system_config import SystemConfigService
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
        log.api.info(f'api-worker 启动：worker={self.worker_name}, thread_pool_size={self.thread_pool_size}')
        futures = {}
        try:
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
                while self.running and len(futures) < self.current_claim_limit():
                    try:
                        case_model = self.claim()
                    except DatabaseError:
                        log.api.warning('event=api_worker_control_unavailable action=pause_claim')
                        connection.close()
                        break
                    if not case_model:
                        break
                    futures[self.executor.submit(self.execute, case_model)] = case_model
                if futures:
                    done, _ = wait(futures, timeout=self.poll_interval, return_when=FIRST_COMPLETED)
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
                    if done and not self.settle_finished(futures, done):
                        time.sleep(self.poll_interval)
                except DatabaseError:
                    connection.close()
                    time.sleep(self.poll_interval)
            self.executor.shutdown(wait=True)
            self.db_context_registry.close_all()
            from src.apps.data_factory.services.datasource_pool import DatasourcePoolRegistry
            from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry
            DatasourcePoolRegistry.close_all()
            ProtocolPoolRegistry.close_all()

    @staticmethod
    def settle_finished(futures, done):
        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
        settled = 0
        for future in done:
            case_model = futures[future]
            try:
                future.result()
            except Exception as error:
                if not getattr(future, '_mango_error_logged', False):
                    log.api.error('event=api_worker_execution_incomplete detail_id=%s exception_type=%s',
                                  case_model.test_suite_details, type(error).__name__)
                    future._mango_error_logged = True
            try:
                ApiWorkerRecoveryService.finish_unreported(case_model.test_suite_details, case_model.attempt)
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
        from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        ServiceHeartbeatService.beat_if_due(
            self,
            RuntimeServiceName.API_WORKER,
            instance_name=self.worker_name,
            metadata={
                **RuntimeProcessIdentity.current(),
                'thread_pool_size': self.thread_pool_size,
                'executor_size': self.executor_size,
                'running_count': len(futures),
                'claim_limit': self.current_claim_limit(),
                'lease_seconds': self.lease_seconds,
                'poll_interval': self.poll_interval,
                'db_idle_seconds': self.db_context_registry.idle_seconds,
                'datasource_maintenance_healthy': DatasourcePoolMaintenance.healthy(),
            },
        )

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
        from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService
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
            from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
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
