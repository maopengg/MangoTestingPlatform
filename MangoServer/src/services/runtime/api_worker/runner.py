import socket
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from django.db import connection

from src.apps.auto_api.service.test_case.test_case import TestCase
from src.apps.task_center.services.claim_service import ApiTaskClaimService
from src.apps.task_center.services.result_service import ScheduleFireResultService
from src.common.tools.decorator.retry import async_task_db_connection
from src.common.tools.log_collector import log
from src.services.runtime.api_worker.db_context import (
    WorkerDbContextRegistry,
    set_current_worker_db_context,
)


class ApiWorkerRunner:
    def __init__(
            self,
            worker_name: str | None = None,
            concurrency: int = 2,
            lease_seconds: int = 1800,
            poll_interval: int = 3,
            db_idle_seconds: int = 1800,
    ):
        self.worker_name = worker_name or socket.gethostname()
        self.concurrency = max(1, concurrency)
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.running = True
        self.db_context_registry = WorkerDbContextRegistry(idle_seconds=db_idle_seconds)
        self.executor = ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix=self.worker_name)

    def run_forever(self):
        log.api.info(f'api-worker 启动：worker={self.worker_name}, concurrency={self.concurrency}')
        futures = set()
        try:
            while self.running:
                while len(futures) < self.concurrency:
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

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def claim(self):
        return ApiTaskClaimService.claim(lease_seconds=self.lease_seconds)

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
                db_context=db_context,
            )
            return test_case.test_case(parametrize=case_model.parametrize)
        finally:
            try:
                ScheduleFireResultService.refresh_by_test_suite(case_model.test_suite)
            except Exception as error:
                log.system.error(f'刷新定时触发结果失败：test_suite={case_model.test_suite}, error={error}')
            try:
                connection.close()
            except Exception:
                pass
            try:
                db_context.close_idle()
            finally:
                set_current_worker_db_context(None)
