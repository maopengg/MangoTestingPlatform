from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.exceptions import (
    TEST_ENVIRONMENT_INVALID,
    TEST_REPORT_NOT_FOUND,
    TEST_REPORT_RETRY_RUNNING,
    TEST_REPORT_EVALUATION_OPERATION_UNSUPPORTED,
    TestCenterError,
)
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService


class TestSuiteRetryService:
    @staticmethod
    def ensure_retry_supported(details):
        if any(getattr(detail, 'type', None) == TestCaseTypeEnum.EVALUATION.value for detail in details):
            raise TestCenterError(TEST_REPORT_EVALUATION_OPERATION_UNSUPPORTED)

    @classmethod
    @transaction.atomic
    def retry_failed(cls, test_suite_id: int) -> int:
        suite = TestSuite.objects.select_for_update().filter(id=test_suite_id).first()
        if suite is None or getattr(suite, 'retained_summary', None):
            raise TestCenterError(TEST_REPORT_NOT_FOUND)
        details = list(TestSuiteDetails.objects.select_for_update().filter(test_suite_id=suite.id))
        cls.ensure_retry_supported(details)
        active = (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)
        if suite.status in active or any(detail.status in active for detail in details):
            raise TestCenterError(TEST_REPORT_RETRY_RUNNING)
        # API 场景可能整体通过但仍有失败计数，重试其所属执行项，不拆散场景步骤。
        failed = [detail for detail in details if not detail.is_excluded and (detail.status == TaskEnum.FAIL.value or detail.fail > 0)]
        if not failed:
            return 0
        for detail in failed:
            cls.retry_detail(detail.id)
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
            cls.refresh_current_api_release(
                detail,
                version_policy_by_case.get(
                    detail.case_id,
                    ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
                ),
            )
        now = timezone.now()
        for detail in details:
            detail.retry = 0
            detail.status = TaskEnum.STAY_BEGIN.value
            detail.error_message = None
            detail.push_time = None
            detail.success = 0
            detail.warning = 0
            detail.fail = 0
            detail.summary_data = None
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
    def retry_detail(cls, test_suite_detail_id: int) -> None:
        detail = TestSuiteDetails.objects.select_for_update().get(id=test_suite_detail_id)
        cls.ensure_retry_supported([detail])
        cls.refresh_current_api_release(detail)
        detail.retry = 0
        detail.status = TaskEnum.STAY_BEGIN.value
        detail.error_message = None
        detail.push_time = None
        detail.success = 0
        detail.warning = 0
        detail.fail = 0
        detail.summary_data = None
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
