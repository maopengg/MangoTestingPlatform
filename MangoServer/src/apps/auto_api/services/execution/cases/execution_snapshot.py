from datetime import datetime
from typing import Any

import time
from mangotools.enums import TaskEnum

from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult, ApiCaseStepResult
from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
from src.common.logging import log


class ApiExecutionSnapshotWriter:
    SNAPSHOT_THRESHOLD_SECONDS = 30
    MIN_SAVE_INTERVAL_SECONDS = 5

    def __init__(
            self,
            test_suite_detail_id: int | None,
            api_case_result: ApiCaseExecutionResult,
            threshold_seconds: int = SNAPSHOT_THRESHOLD_SECONDS,
            min_interval_seconds: int = MIN_SAVE_INTERVAL_SECONDS,
    ):
        self.test_suite_detail_id = test_suite_detail_id
        self.api_case_result = api_case_result
        self.threshold_seconds = threshold_seconds
        self.min_interval_seconds = min_interval_seconds
        self.start_monotonic = time.monotonic()
        self.last_save_monotonic = 0.0

    def maybe_save(
            self,
            *,
            reason: str,
            current_step: ApiCaseStepResult | None = None,
            retry_current: int | None = None,
            retry_max: int | None = None,
            force: bool = False,
    ):
        if not self.test_suite_detail_id:
            return
        now_monotonic = time.monotonic()
        elapsed = now_monotonic - self.start_monotonic
        if not force and elapsed < self.threshold_seconds:
            return
        if not force and self.last_save_monotonic and now_monotonic - self.last_save_monotonic < self.min_interval_seconds:
            return
        try:
            detail = TestSuiteDetails.objects.get(id=self.test_suite_detail_id)
            if detail.status != TaskEnum.PROCEED.value:
                return
            TestSuiteExecutionResultService.save_snapshot(
                detail,
                self.build_snapshot(
                    detail,
                    reason=reason,
                    current_step=current_step,
                    retry_current=retry_current,
                    retry_max=retry_max,
                    elapsed=elapsed,
                ),
            )
            self.last_save_monotonic = now_monotonic
        except Exception as error:
            log.api.error(f'保存API执行快照失败：{error}')

    def build_snapshot(
            self,
            detail: TestSuiteDetails,
            *,
            reason: str,
            current_step: ApiCaseStepResult | None,
            retry_current: int | None,
            retry_max: int | None,
            elapsed: float,
    ) -> dict[str, Any]:
        steps = [item.model_dump() for item in self.api_case_result.steps]
        current_step_data = current_step.model_dump() if current_step else (steps[-1] if steps else None)
        progress_done = len(TestSuiteExecutionResultService.only_last_api_retry_results(steps))
        retry_data = None
        if retry_current is not None or retry_max is not None:
            retry_data = {
                'current': retry_current,
                'max': retry_max,
                'reason': getattr(current_step, 'error_message', None) if current_step else None,
            }
        return {
            'result_mode': 'snapshot',
            'status': 'running',
            'reason': reason,
            'elapsed': round(elapsed, 3),
            'progress': {
                'total': detail.case_sum or 0,
                'done': progress_done,
                'current_index': min(progress_done + 1, detail.case_sum or progress_done + 1),
                'current_name': getattr(current_step, 'name', None) if current_step else None,
            },
            'retry': retry_data,
            'steps': steps,
            'current_step': current_step_data,
            'cache': current_step.cache_data if current_step else {},
            'data_factory_cache': current_step.data_factory_cache_data if current_step else {},
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
