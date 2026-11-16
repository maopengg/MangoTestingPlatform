from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService

from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.exceptions import (
    TEST_ENVIRONMENT_INVALID,
    TEST_REPORT_NOT_FOUND,
    TEST_REPORT_RETRY_RUNNING,
    TEST_REPORT_EVALUATION_OPERATION_UNSUPPORTED,
    TEST_REPORT_INFRASTRUCTURE_REVIEW_REQUIRED,
    TEST_REPORT_INFRASTRUCTURE_REVIEW_STALE,
    TEST_REPORT_INFRASTRUCTURE_RESOURCES_UNREADY,
    TestCenterError,
)
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService


class TestSuiteRetryService:
    @staticmethod
    def ensure_infrastructure_reviewed(detail, *, confirmed=False):
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        if (getattr(detail, 'status', None) == TaskEnum.INFRASTRUCTURE_BLOCKED.value
                or TestSuiteInfrastructureService.is_blocked(detail.summary_data)):
            control = (detail.summary_data or {}).get('meta', {}).get('execution_control', {})
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            # 人工核查不是永久通行证；重试前名额、清理状态变化仍须拒绝重放。
            if control.get('requires_review', True) and not confirmed:
                raise TestCenterError(TEST_REPORT_INFRASTRUCTURE_REVIEW_REQUIRED)
            if control.get('attempt', detail.retry) != detail.retry:
                raise TestCenterError(TEST_REPORT_INFRASTRUCTURE_REVIEW_STALE)
            if not DatasourceInfrastructureService.cleanup_review_ready(detail.id, detail.retry):
                raise TestCenterError(TEST_REPORT_INFRASTRUCTURE_RESOURCES_UNREADY)

    @staticmethod
    def ensure_retry_supported(details):
        if any(getattr(detail, 'type', None) == TestCaseTypeEnum.EVALUATION.value for detail in details):
            raise TestCenterError(TEST_REPORT_EVALUATION_OPERATION_UNSUPPORTED)

    @classmethod
    @transaction.atomic
    def retry_failed(cls, test_suite_id: int, *, confirm_infrastructure_retry=False, user=None) -> int:
        suite = TestSuite.objects.select_for_update().filter(id=test_suite_id).first()
        if suite is None or getattr(suite, 'retained_summary', None):
            raise TestCenterError(TEST_REPORT_NOT_FOUND)
        details = list(TestSuiteDetails.objects.select_for_update().filter(test_suite_id=suite.id))
        cls.ensure_retry_supported(details)
        active = (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)
        if suite.status in active or any(detail.status in active for detail in details):
            raise TestCenterError(TEST_REPORT_RETRY_RUNNING)
        # API 场景可能整体通过但仍有失败计数，重试其所属执行项，不拆散场景步骤。
        failed = [detail for detail in details if not detail.is_excluded and (
            detail.status in (TaskEnum.FAIL.value, TaskEnum.INFRASTRUCTURE_BLOCKED.value) or detail.fail > 0)]
        if not failed:
            return 0
        for detail in failed:
            cls.retry_detail(detail.id, confirm_infrastructure_retry=confirm_infrastructure_retry, user=user)
        TestSuite.objects.filter(id=suite.id).update(status=TaskEnum.STAY_BEGIN.value, update_time=timezone.now())
        return len(failed)

    @staticmethod
    def refresh_current_api_release(
            detail: TestSuiteDetails,
            version_policy: str | None = None,
    ) -> None:
        if detail.type != TestCaseTypeEnum.API.value:
            return
        if not detail.api_case_release_id and not detail.test_suite.tasks_id:
            selection = ApiCaseRevisionService.resolve_manual_revision_retry(
                detail.case_id, detail.api_case_revision_id,
            )
            if selection is not None:
                detail.api_case_revision_id = selection.case_revision_id
                detail.config_checksum = selection.checksum
                return
            # 手动批量执行选择编辑态时，重试继续执行当前编辑态。
            # 同时兼容清理旧版批量执行曾绑定的未发布执行快照。
            detail.api_case_revision_id = None
            detail.api_case_release_id = None
            detail.config_checksum = None
            return
        if version_policy is None:
            version_policy = ApiCaseTaskBindingService.report_detail_version_policy(detail)
        selection = ApiCaseTaskBindingService.resolve_execution_selection(
            detail.case_id,
            version_policy,
        )
        detail.api_case_revision_id = selection.case_revision_id if selection else None
        detail.api_case_release_id = selection.case_release_id if selection else None
        detail.config_checksum = selection.checksum if selection else None

    @staticmethod
    def resolve_test_env(value, default: int) -> int:
        if value is None or value == '':
            return default
        if isinstance(value, (bool, float)):
            raise TestCenterError(TEST_ENVIRONMENT_INVALID)
        try:
            test_env = int(value)
        except (TypeError, ValueError) as error:
            raise TestCenterError(TEST_ENVIRONMENT_INVALID, error=str(error)) from error
        if test_env not in EnvironmentEnum.get_key_list():
            raise TestCenterError(TEST_ENVIRONMENT_INVALID)
        return test_env

    @classmethod
    @transaction.atomic
    def retry_all(
            cls,
            test_suite_id,
            test_env=None,
            api_concurrency_limit=None,
            concurrency_override_provided: bool = False,
            confirm_infrastructure_retry: bool = False,
            user=None,
    ) -> tuple[int, int | None]:
        test_suite = TestSuite.objects.select_for_update().filter(id=test_suite_id).first()
        if not test_suite or getattr(test_suite, 'retained_summary', None):
            raise TestCenterError(TEST_REPORT_NOT_FOUND)

        resolved_test_env = cls.resolve_test_env(test_env, test_suite.test_env)
        resolved_concurrency_limit = test_suite.api_concurrency_limit
        if concurrency_override_provided:
            resolved_concurrency_limit = ApiConcurrencyService.resolve_report_limit(
                api_concurrency_limit,
                TestCenterError,
            )
        details = list(
            TestSuiteDetails.objects.select_for_update().filter(test_suite_id=test_suite.id)
        )
        active = (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)
        if test_suite.status in active or any(detail.status in active for detail in details):
            raise TestCenterError(TEST_REPORT_RETRY_RUNNING)
        detail_ids = [detail.id for detail in details]
        cls.ensure_retry_supported(details)
        version_policy_by_case = {}
        if test_suite.tasks_id:
            from src.apps.task_center.models import TasksDetails
            version_policy_by_case = dict(
                TasksDetails.objects.filter(
                    task_id=test_suite.tasks_id,
                    type=TestCaseTypeEnum.API.value,
                ).values_list('api_case_id', 'version_policy')
            )
        for detail in details:
            cls.ensure_infrastructure_reviewed(detail, confirmed=confirm_infrastructure_retry)
            cls.refresh_current_api_release(
                detail,
                version_policy_by_case.get(
                    detail.case_id,
                    ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
                ),
            )
        now = timezone.now()
        for detail in details:
            prior_control = (detail.summary_data or {}).get('meta', {}).get('execution_control')
            detail.retry = 0
            detail.status = TaskEnum.STAY_BEGIN.value
            detail.error_message = None
            detail.push_time = None
            detail.success = 0
            detail.warning = 0
            detail.fail = 0
            detail.summary_data = ApiReportCountingService.empty_summary(detail)
            if prior_control:
                detail.summary_data = detail.summary_data or {}
                detail.summary_data.setdefault('meta', {})['retry_confirmation'] = {
                    'previous_attempt': prior_control.get('attempt'),
                    'previous_observed_at': prior_control.get('observed_at'),
                    'confirmed_at': now.isoformat(), 'confirmed_by': getattr(user, 'id', None),
                }
            detail.is_excluded = False
            detail.failure_reason = ''
            detail.failure_description = ''
            detail.test_env = resolved_test_env
            detail.update_time = now
        TestSuiteDetails.objects.bulk_update(
            details,
            [
                'retry',
                'status',
                'error_message',
                'push_time',
                'success',
                'warning',
                'fail',
                'summary_data',
                'is_excluded',
                'failure_reason',
                'failure_description',
                'test_env',
                'api_case_revision',
                'api_case_release',
                'config_checksum',
                'update_time',
            ],
        )
        TestSuiteExecutionResultService.clear_result(detail_ids)
        TestSuite.objects.filter(id=test_suite.id).update(
            status=TaskEnum.STAY_BEGIN.value,
            test_env=resolved_test_env,
            api_concurrency_limit=resolved_concurrency_limit,
            update_time=now,
        )
        return resolved_test_env, resolved_concurrency_limit

    @classmethod
    @transaction.atomic
    def retry_detail(cls, test_suite_detail_id: int, *, confirm_infrastructure_retry=False, user=None) -> None:
        detail = TestSuiteDetails.objects.select_for_update().get(id=test_suite_detail_id)
        if detail.status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
            raise TestCenterError(TEST_REPORT_RETRY_RUNNING)
        cls.ensure_infrastructure_reviewed(detail, confirmed=confirm_infrastructure_retry)
        cls.ensure_retry_supported([detail])
        cls.refresh_current_api_release(detail)
        prior_control = (detail.summary_data or {}).get('meta', {}).get('execution_control')
        detail.retry = 0
        detail.status = TaskEnum.STAY_BEGIN.value
        detail.error_message = None
        detail.push_time = None
        detail.success = 0
        detail.warning = 0
        detail.fail = 0
        detail.summary_data = ApiReportCountingService.empty_summary(detail)
        if prior_control:
            detail.summary_data = detail.summary_data or {}
            detail.summary_data.setdefault('meta', {})['retry_confirmation'] = {
                'previous_attempt': prior_control.get('attempt'),
                'previous_observed_at': prior_control.get('observed_at'),
                'confirmed_at': timezone.now().isoformat(),
                'confirmed_by': getattr(user, 'id', None),
            }
        detail.is_excluded = False
        detail.failure_reason = ''
        detail.failure_description = ''
        detail.save(update_fields=[
            'retry',
            'status',
            'error_message',
            'push_time',
            'success',
            'warning',
            'fail',
            'summary_data',
            'is_excluded',
            'failure_reason',
            'failure_description',
            'api_case_revision',
            'api_case_release',
            'config_checksum',
            'update_time',
        ])
        TestSuiteExecutionResultService.clear_result([detail.id])
