import socket
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import time
from django.db import connection

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
        futures = set()
        try:
            while self.running:
                self.refresh_thread_pool_size(futures)
                self.report_heartbeat(futures)
                while len(futures) < self.current_claim_limit():
                    case_model = self.claim()
                    if not case_model:
                        break
                    futures.add(self.executor.submit(self.execute, case_model))
                if futures:
                    done, futures = wait(futures, timeout=self.poll_interval, return_when=FIRST_COMPLETED)
                    for future in done:
                        try:
                            future.result()
                        except Exception as error:
                            log.api.error(f'api-worker 执行任务异常：{error}')
                else:
                    time.sleep(self.poll_interval)
        finally:
            self.executor.shutdown(wait=True)
            self.db_context_registry.close_all()

    def create_executor(self, thread_pool_size: int):
        return ThreadPoolExecutor(max_workers=thread_pool_size, thread_name_prefix=self.worker_name)

    def current_claim_limit(self):
        return min(self.thread_pool_size, self.executor_size)

    def refresh_thread_pool_size(self, futures: set):
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

    def report_heartbeat(self, futures: set):
        ServiceHeartbeatService.beat_if_due(
            self,
            RuntimeServiceName.API_WORKER,
            instance_name=self.worker_name,
            metadata={
                'thread_pool_size': self.thread_pool_size,
                'executor_size': self.executor_size,
                'running_count': len(futures),
                'claim_limit': self.current_claim_limit(),
                'lease_seconds': self.lease_seconds,
                'poll_interval': self.poll_interval,
                'db_idle_seconds': self.db_context_registry.idle_seconds,
            },
        )

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def claim(self):
        return ApiTaskClaimService.claim(lease_seconds=self.lease_seconds)

    @system_error_guard(
        source=SystemErrorEventSource.API_WORKER,
        request_path='execute_api_case',
        service_name=RuntimeServiceName.API_WORKER,
    )
    def execute(self, case_model):
        db_context = self.db_context_registry.current()
        set_current_worker_db_context(db_context)
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
            return test_case.test_case(parametrize=case_model.parametrize)
        finally:
            try:
                connection.close()
            except Exception:
                pass
            try:
                db_context.close_idle()
            finally:
                set_current_worker_db_context(None)
