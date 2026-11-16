import os
import uuid
import socket
from functools import wraps
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from typing import Any

import time
from django.utils import timezone

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStatus, ApiCaseTraceStepType
from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace
from src.apps.auto_api.services.execution_trace.context import ApiCaseExecutionContext
from src.common.logging import log

_execution_trace = ContextVar('api_execution_trace', default=None)


def current_execution_trace():
    recorder = _execution_trace.get()
    return recorder.trace if recorder is not None else None


def trace_lifecycle(stage):
    def decorate(function):
        @wraps(function)
        def guarded(self, *args, **kwargs):
            try:
                recorder = getattr(self, 'trace_recorder', None)
                with recorder.execution_scope() if recorder is not None else nullcontext():
                    return function(self, *args, **kwargs)
            except BaseException as error:
                recorder = getattr(self, 'trace_recorder', None)
                if recorder is not None:
                    recorder.abort_trace(error, stage)
                raise
        return guarded
    return decorate


class ApiCaseExecutionTraceRecorder:
    """API Case Trace，记录失败不覆盖原执行异常。

    summary生命周期字段：execution_owner={process_token, process_started_at}；
    review_required为布尔；interrupted_stage为Trace阶段；exception_type仅保存类名。
    对账额外保存reconciled_at（ISO时间）、execution_result_id（精确结果ID或null）。
    """

    SUMMARY_TEXT_LIMIT = 1000

    @staticmethod
    def interrupt_open_steps(trace_id, ended, message):
        ApiCaseExecutionStep.objects.filter(trace_id=trace_id, status=ApiCaseTraceStatus.PROCEED).update(
            status=ApiCaseTraceStatus.FAIL, finished_at=ended, error_message=message, update_time=ended)

    @staticmethod
    def interrupt_report_attempt(detail_id, pushed_at, message, control):
        now = timezone.now()
        traces = ApiCaseExecutionTrace.objects.filter(
            test_suite_detail_id=detail_id, status=ApiCaseTraceStatus.PROCEED,
        )
        if pushed_at is not None:
            traces = traces.filter(started_at__gte=pushed_at)
        for trace in traces:
            for step in ApiCaseExecutionStep.objects.filter(trace=trace, status=ApiCaseTraceStatus.PROCEED):
                step.status = ApiCaseTraceStatus.FAIL
                step.finished_at = now
                step.duration_ms = max(0, int((now - (step.started_at or now)).total_seconds() * 1000))
                step.error_message = message
                step.save(update_fields=['status', 'finished_at', 'duration_ms', 'error_message', 'update_time'])
            trace.status = ApiCaseTraceStatus.FAIL
            trace.finished_at = now
            trace.duration_ms = max(0, int((now - (trace.started_at or now)).total_seconds() * 1000))
            trace.error_message = message
            trace.summary = {**(trace.summary if isinstance(trace.summary, dict) else {}),
                             'execution_control': control}
            trace.save(update_fields=['status', 'finished_at', 'duration_ms', 'error_message', 'summary', 'update_time'])

    def __init__(self):
        self.trace: ApiCaseExecutionTrace | None = None
        self._sort = 0
        self._start_time = time.time()
        self._custom_depth = 0
        self._last_request_progress = float('-inf')

    @contextmanager
    def execution_scope(self):
        token = _execution_trace.set(self)
        try:
            yield
        finally:
            _execution_trace.reset(token)

    @contextmanager
    def custom_function(self):
        self._custom_depth += 1
        try:
            yield
        finally:
            self._custom_depth -= 1

    def record_request_progress(self):
        """只有自定义函数内真实返回的接口调用才是进展，存活和续租不作为进展。"""
        now = time.monotonic()
        if (not self._custom_depth or self.trace is None or self.trace.finished_at is not None
                or self.trace.status != ApiCaseTraceStatus.PROCEED or now - self._last_request_progress < 15):
            return
        self._last_request_progress = now
        step = self.start_step(ApiCaseTraceStepType.REQUEST, '自定义函数内部接口调用完成',
                               input_summary={'internal_call': True})
        self.finish_step(step)

    def create_trace(self, context: ApiCaseExecutionContext) -> ApiCaseExecutionTrace | None:
        try:
            from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
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
                worker_name=context.worker_name or os.getenv('HOSTNAME') or socket.gethostname(),
                started_at=now,
                summary={**self._safe_summary(context.summary), 'execution_owner': RuntimeProcessIdentity.current()},
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

    def abort_trace(self, error, stage):
        from src.common.exceptions import MangoServerError
        from src.apps.auto_api.exceptions import API_CASE_TRACE_INTERRUPTED
        expected = isinstance(error, MangoServerError)
        message = error.msg if expected else API_CASE_TRACE_INTERRUPTED.message
        self.fail_trace(message, {'review_required': not expected, 'interrupted_stage': stage,
                                 'exception_type': type(error).__name__})

    @contextmanager
    def guard(self, stage):
        try:
            yield
        except BaseException as error:
            self.abort_trace(error, stage)
            raise

    def update_metadata(self, case_name, summary):
        if self.trace is None:
            return
        try:
            self.trace.case_name = case_name
            self.trace.summary = {**self.trace.summary, **self._safe_summary(summary)}
            self.trace.save(update_fields=['case_name', 'summary', 'update_time'])
        except Exception:
            log.api.exception('API执行链路初始化信息保存失败')

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
                    'review_required': isinstance(summary, dict) and summary.get('review_required') is True,
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
