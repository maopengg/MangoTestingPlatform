import os
import uuid
from typing import Any

import time
from django.utils import timezone

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStatus, ApiCaseTraceStepType
from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace
from src.apps.auto_api.services.execution_trace.context import ApiCaseExecutionContext
from src.common.logging import log


class ApiCaseExecutionTraceRecorder:
    """API case 执行链路记录器。所有记录失败都只打日志，不影响主执行流程。"""

    SUMMARY_TEXT_LIMIT = 1000

    def __init__(self):
        self.trace: ApiCaseExecutionTrace | None = None
        self._sort = 0
        self._start_time = time.time()

    def create_trace(self, context: ApiCaseExecutionContext) -> ApiCaseExecutionTrace | None:
        try:
            now = timezone.now()
            self._start_time = time.time()
            self.trace = ApiCaseExecutionTrace.objects.create(
                trace_id=uuid.uuid4().hex,
                source_type=context.source_type,
                test_suite_id=context.test_suite_id,
                test_suite_detail_id=context.test_suite_detail_id,
                case_id=context.case_id,
                case_name=context.case_name,
                user_id=context.user_id,
                test_env=context.test_env,
                status=ApiCaseTraceStatus.PROCEED,
                worker_name=context.worker_name or os.getenv('HOSTNAME'),
                started_at=now,
                summary=self._safe_summary(context.summary),
            )
            return self.trace
        except Exception as error:
            log.api.error(f'API执行链路trace创建失败：{error}')
            self.trace = None
            return None

    def start_step(
            self,
            step_type: str,
            step_name: str,
            input_summary: Any = None,
            detail_ref_type: str | None = None,
            detail_ref_id: str | int | None = None,
            parent_step_id: int | None = None,
    ) -> ApiCaseExecutionStep | None:
        if not self.trace:
            return None
        try:
            self._sort += 1
            return ApiCaseExecutionStep.objects.create(
                trace=self.trace,
                parent_step_id=parent_step_id,
                step_key=f'{step_type}:{self._sort}',
                step_type=step_type,
                step_name=step_name,
                status=ApiCaseTraceStatus.PROCEED,
                sort=self._sort,
                started_at=timezone.now(),
                input_summary=self._safe_summary(input_summary),
                detail_ref_type=detail_ref_type,
                detail_ref_id=str(detail_ref_id) if detail_ref_id is not None else None,
            )
        except Exception as error:
            log.api.error(f'API执行链路step创建失败：{error}')
            return None

    def finish_step(self, step: ApiCaseExecutionStep | None, output_summary: Any = None):
        self._close_step(step, ApiCaseTraceStatus.SUCCESS, output_summary=output_summary)

    def fail_step(self, step: ApiCaseExecutionStep | None, error_message: str | None, output_summary: Any = None):
        self._close_step(step, ApiCaseTraceStatus.FAIL, error_message=error_message, output_summary=output_summary)

    def skip_step(self, step_name: str, output_summary: Any = None, detail_ref_type: str | None = None,
                  detail_ref_id: str | int | None = None):
        step = self.start_step(ApiCaseTraceStepType.SKIPPED, step_name, detail_ref_type=detail_ref_type,
                               detail_ref_id=detail_ref_id)
        self._close_step(step, ApiCaseTraceStatus.SKIP, output_summary=output_summary)

    def finish_trace(self, summary: Any = None):
        self._close_trace(ApiCaseTraceStatus.SUCCESS, summary=summary)

    def fail_trace(self, error_message: str | None, summary: Any = None):
        self._close_trace(ApiCaseTraceStatus.FAIL, error_message=error_message, summary=summary)

    def _close_step(
            self,
            step: ApiCaseExecutionStep | None,
            status: int,
            error_message: str | None = None,
            output_summary: Any = None,
    ):
        if not step:
            return
        try:
            now = timezone.now()
            started_at = step.started_at or now
            step.status = status
            step.finished_at = now
            step.duration_ms = max(0, int((now - started_at).total_seconds() * 1000))
            step.error_message = self._safe_text(error_message) if error_message else None
            step.output_summary = self._safe_summary(output_summary)
            step.save(update_fields=[
                'status',
                'finished_at',
                'duration_ms',
                'error_message',
                'output_summary',
                'update_time',
            ])
        except Exception as error:
            log.api.error(f'API执行链路step结束记录失败：{error}')

    def _close_trace(self, status: int, error_message: str | None = None, summary: Any = None):
        if not self.trace:
            return
        try:
            now = timezone.now()
            self.trace.status = status
            self.trace.finished_at = now
            self.trace.duration_ms = max(0, int((time.time() - self._start_time) * 1000))
            self.trace.error_message = self._safe_text(error_message) if error_message else None
            if summary is not None:
                existing_summary = self.trace.summary if isinstance(self.trace.summary, dict) else {}
                self.trace.summary = {
                    **existing_summary,
                    **self._safe_summary(summary),
                }
            self.trace.save(update_fields=[
                'status',
                'finished_at',
                'duration_ms',
                'error_message',
                'summary',
                'update_time',
            ])
        except Exception as error:
            log.api.error(f'API执行链路trace结束记录失败：{error}')

    def _safe_summary(self, value: Any) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(key): self._safe_value(val) for key, val in value.items()}
        return {'value': self._safe_value(value)}

    def _safe_value(self, value: Any):
        if isinstance(value, dict):
            return {str(key): self._safe_value(val) for key, val in value.items() if
                    not self._is_sensitive_key(str(key))}
        if isinstance(value, list):
            return [self._safe_value(item) for item in value[:20]]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return self._safe_text(value)
        if hasattr(value, 'model_dump'):
            return self._safe_value(value.model_dump())
        return self._safe_text(value)

    def _safe_text(self, value: Any) -> str:
        text = str(value)
        if len(text) > self.SUMMARY_TEXT_LIMIT:
            return f'{text[:self.SUMMARY_TEXT_LIMIT]}...'
        return text

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        lowered = key.lower()
        return any(word in lowered for word in ['authorization', 'token', 'password', 'secret', 'cookie'])
