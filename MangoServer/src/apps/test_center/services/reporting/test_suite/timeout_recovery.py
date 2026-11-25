from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.reporting import ReportRecoveryCauseEnum
from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService


class TestSuiteTimeoutRecoveryService:
    """统一收口测试报告中被系统超时重置的明细。"""

    TERMINATION_TYPE = 'system_timeout_reset'
    TYPE_NAMES = {
        TestCaseTypeEnum.API.value: 'API Case',
        TestCaseTypeEnum.UI.value: 'UI Case',
        TestCaseTypeEnum.PYTEST.value: 'Pytest Case',
    }
    CHECK_HINTS = {
        TestCaseTypeEnum.API.value: '请检查强制等待、SQL、自定义函数、外部依赖或 API Worker 状态后重试。',
        TestCaseTypeEnum.UI.value: '请检查页面等待、脚本步骤、浏览器或执行器状态后重试。',
        TestCaseTypeEnum.PYTEST.value: '请检查测试代码、阻塞调用、Fixture 或执行器状态后重试。',
    }

    @classmethod
    @transaction.atomic
    def reset_for_retry(cls, detail: TestSuiteDetails, timeout_minutes: int, max_attempts: int):
        from src.apps.test_center.models import TestSuite
        TestSuite.objects.select_for_update().get(id=detail.test_suite_id)
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail.id)
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        if TestSuiteInfrastructureService.is_blocked(detail.summary_data):
            return False
        if (detail.type == TestCaseTypeEnum.API.value and detail.status == TaskEnum.PROCEED.value
                and detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=timeout_minutes)):
            TestSuiteInfrastructureService.block(detail.id, max(1, int(detail.retry or 0)), [],
                cause=ReportRecoveryCauseEnum.EXECUTION_TIMEOUT,
                interruption_reason=f'执行超过 {timeout_minutes} 分钟未完成。请核查执行进展及数据清理状态')
            return False
        if not cls.can_reset(detail, timeout_minutes, max_attempts):
            return False
        from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
        if TaskCenterQuerySelector.cleanup_for_case_attempt(detail.id, int(detail.retry or 0)).exists():
            cls.fail_cleanup_interrupted(detail)
            return False
        current_attempt = max(1, int(detail.retry or 0))
        next_attempt = min(current_attempt + 1, max_attempts)
        detail.status = TaskEnum.STAY_BEGIN.value
        detail.error_message = cls.retry_message(
            detail.type,
            timeout_minutes,
            current_attempt,
            next_attempt,
            max_attempts,
        )
        detail.save(update_fields=['status', 'error_message', 'update_time'])
        cls.project_business_status(detail, TaskEnum.STAY_BEGIN.value)
        return True

    @classmethod
    @transaction.atomic
    def fail_cleanup_interrupted(cls, detail):
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail.id)
        if detail.status != TaskEnum.PROCEED.value:
            return False
        now = timezone.now()
        message = '原执行在数据工厂清理阶段失联或超时；清理任务继续保留，不自动重放已执行的业务步骤，请检查后重新发起完整测试'
        termination = {'type': 'data_factory_cleanup_interrupted', 'attempt': int(detail.retry or 0),
                       'terminated_at': now.isoformat(), 'message': message, 'has_test_result': False}
        trace_id = cls.close_api_traces(detail, message, termination, now)
        detail.status, detail.error_message = TaskEnum.FAIL.value, message
        detail.success = detail.fail = detail.warning = 0
        counting = ApiReportCountingService.empty_summary(detail) or {'meta': {}}
        detail.summary_data = {'children': None, 'meta': {**counting['meta'], 'termination': termination}}
        detail.save(update_fields=['status', 'error_message', 'success', 'fail', 'warning', 'summary_data', 'update_time'])
        cls.save_empty_execution_record(detail, message, trace_id)
        cls.project_business_status(detail, TaskEnum.FAIL.value)
        return True

    @classmethod
    @transaction.atomic
    def fail_after_retries(cls, detail: TestSuiteDetails, timeout_minutes: int, max_attempts: int):
        from src.apps.test_center.models import TestSuite
        TestSuite.objects.select_for_update().get(id=detail.test_suite_id)
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail.id)
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        if TestSuiteInfrastructureService.is_blocked(detail.summary_data):
            return False
        if (detail.type == TestCaseTypeEnum.API.value and detail.status == TaskEnum.PROCEED.value
                and detail.push_time and timezone.now() - detail.push_time > timedelta(minutes=timeout_minutes)):
            TestSuiteInfrastructureService.block(detail.id, max(1, int(detail.retry or 0)), [],
                cause=ReportRecoveryCauseEnum.EXECUTION_TIMEOUT,
                interruption_reason=f'执行超过 {timeout_minutes} 分钟未完成。请核查执行进展及数据清理状态')
            return False
        if not cls.can_terminate(detail, timeout_minutes, max_attempts):
            return False
        now = timezone.now()
        message = cls.failure_message(detail.type, timeout_minutes, max_attempts)
        termination = {
            'type': cls.TERMINATION_TYPE,
            'timeout_minutes': timeout_minutes,
            'attempt': int(detail.retry or max_attempts),
            'max_attempts': max_attempts,
            'terminated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            'message': message,
            'has_test_result': False,
        }
        trace_id = cls.close_api_traces(detail, message, termination, now)
        detail.status = TaskEnum.FAIL.value
        detail.error_message = message
        detail.success = 0
        detail.fail = 0
        detail.warning = 0
        counting = ApiReportCountingService.empty_summary(detail) or {'meta': {}}
        detail.summary_data = {
            'children': None,
            'meta': {**counting['meta'], 'termination': termination},
        }
        detail.save(update_fields=[
            'status',
            'error_message',
            'success',
            'fail',
            'warning',
            'summary_data',
            'update_time',
        ])
        cls.save_empty_execution_record(detail, message, trace_id)
        cls.project_business_status(detail, TaskEnum.FAIL.value)
        return True

    @staticmethod
    def project_business_status(detail: TestSuiteDetails, status: int) -> int:
        if detail.type == TestCaseTypeEnum.API.value:
            from src.apps.auto_api.services.execution.cases.run_status import ApiCaseRunStatusService

            return ApiCaseRunStatusService.project_status(detail.case_id, status)
        if detail.type == TestCaseTypeEnum.UI.value:
            from src.apps.auto_ui.services.execution.execution_status import UiExecutionStatusService

            return UiExecutionStatusService.project_case_status(detail.case_id, status)
        if detail.type == TestCaseTypeEnum.PYTEST.value:
            from src.apps.auto_pytest.services.execution.execution_status import PytestExecutionStatusService

            return PytestExecutionStatusService.project_status(detail.case_id, status)
        return 0

    @staticmethod
    def can_reset(detail: TestSuiteDetails, timeout_minutes: int, max_attempts: int) -> bool:
        return bool(
            detail.status == TaskEnum.PROCEED.value
            and int(detail.retry or 0) < max_attempts
            and detail.push_time
            and timezone.now() - detail.push_time > timedelta(minutes=timeout_minutes)
        )

    @staticmethod
    def can_terminate(detail: TestSuiteDetails, timeout_minutes: int, max_attempts: int) -> bool:
        return bool(
            detail.status in [TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value]
            and int(detail.retry or 0) >= max_attempts
            and detail.push_time
            and timezone.now() - detail.push_time > timedelta(minutes=timeout_minutes)
        )

    @classmethod
    def is_timeout_terminated(cls, detail: TestSuiteDetails) -> bool:
        summary_data = detail.summary_data if isinstance(detail.summary_data, dict) else {}
        meta = summary_data.get('meta') if isinstance(summary_data.get('meta'), dict) else {}
        termination = meta.get('termination') if isinstance(meta.get('termination'), dict) else {}
        return bool(
            detail.status == TaskEnum.FAIL.value
            and termination.get('type') == cls.TERMINATION_TYPE
        )

    @classmethod
    def failure_message(cls, case_type: int, timeout_minutes: int, max_attempts: int) -> str:
        return (
            f'系统检测到该{cls.type_name(case_type)}连续{max_attempts}次执行均超过{timeout_minutes}分钟，'
            '已被系统超时重置并终止。执行进程未正常回传，因此本次没有生成测试结果。'
            f'{cls.CHECK_HINTS.get(case_type, "请检查执行配置和执行节点状态后重试。")}'
        )

    @classmethod
    def retry_message(
            cls,
            case_type: int,
            timeout_minutes: int,
            current_attempt: int,
            next_attempt: int,
            max_attempts: int,
    ) -> str:
        return (
            f'系统检测到本次{cls.type_name(case_type)}执行超过{timeout_minutes}分钟且未回传结果，'
            f'已进行第{current_attempt}次超时重置，将自动发起第{next_attempt}/{max_attempts}次执行。'
        )

    @classmethod
    def type_name(cls, case_type: int) -> str:
        return cls.TYPE_NAMES.get(case_type, '自动化用例')

    @classmethod
    def save_empty_execution_record(
            cls,
            detail: TestSuiteDetails,
            message: str,
            trace_id: str | None,
    ):
        ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            target_type=cls.target_type(detail.type),
            target_id=detail.case_id,
            result_data=None,
            test_env=detail.test_env,
            revision_id=detail.api_case_revision_id,
            release_id=detail.api_case_release_id,
            test_suite_id=detail.test_suite_id,
            test_suite_detail_id=detail.id,
            status=TaskEnum.FAIL.value,
            error_message=message,
            trace_id=trace_id,
        )

    @staticmethod
    def target_type(case_type: int) -> str:
        if case_type == TestCaseTypeEnum.API.value:
            return ExecutionResultService.TARGET_API_CASE
        if case_type == TestCaseTypeEnum.UI.value:
            return ExecutionResultService.TARGET_UI_CASE
        if case_type == TestCaseTypeEnum.PYTEST.value:
            return ExecutionResultService.TARGET_PYTEST_CASE
        return 'unknown'

    @classmethod
    def close_api_traces(
            cls,
            detail: TestSuiteDetails,
            message: str,
            termination: dict,
            now,
    ) -> str | None:
        if detail.type != TestCaseTypeEnum.API.value:
            return None
        from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace

        traces = list(
            ApiCaseExecutionTrace.objects.filter(
                test_suite_detail_id=detail.id,
                status=TaskEnum.PROCEED.value,
            ).order_by('create_time', 'id')
        )
        for trace in traces:
            steps = ApiCaseExecutionStep.objects.filter(
                trace=trace,
                status=TaskEnum.PROCEED.value,
            )
            for step in steps:
                started_at = step.started_at or now
                step.status = TaskEnum.FAIL.value
                step.finished_at = now
                step.duration_ms = max(0, int((now - started_at).total_seconds() * 1000))
                step.error_message = message
                step.save(update_fields=[
                    'status',
                    'finished_at',
                    'duration_ms',
                    'error_message',
                    'update_time',
                ])
            started_at = trace.started_at or now
            trace.status = TaskEnum.FAIL.value
            trace.finished_at = now
            trace.duration_ms = max(0, int((now - started_at).total_seconds() * 1000))
            trace.error_message = message
            trace.summary = {
                **(trace.summary if isinstance(trace.summary, dict) else {}),
                'termination': termination,
            }
            trace.save(update_fields=[
                'status',
                'finished_at',
                'duration_ms',
                'error_message',
                'summary',
                'update_time',
            ])
        return traces[-1].trace_id if traces else None
