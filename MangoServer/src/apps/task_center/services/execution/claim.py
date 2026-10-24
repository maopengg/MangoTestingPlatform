import threading
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256

from django.db import connection, transaction
from django.db.models import F, Min, Q
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.schemas.execution import ExecutionCaseCommand
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock

_NON_MYSQL_PLATFORM_CLAIM_LOCK = threading.Lock()


class ApiTaskClaimService:
    PLATFORM_LOCK_PREFIX = 'mango:api:claim'
    PLATFORM_LOCK_TIMEOUT_SECONDS = 1

    @classmethod
    def platform_lock_name(cls) -> str:
        database_name = str(connection.settings_dict.get('NAME') or 'default')
        database_hash = sha256(database_name.encode('utf-8')).hexdigest()[:16]
        return f'{cls.PLATFORM_LOCK_PREFIX}:{database_hash}'

    @classmethod
    @contextmanager
    def platform_claim_lock(cls):
        if connection.vendor == 'mysql':
            lock_name = cls.platform_lock_name()
            acquired = acquire_mysql_lock(lock_name, timeout=cls.PLATFORM_LOCK_TIMEOUT_SECONDS)
            try:
                yield acquired
            finally:
                if acquired:
                    release_mysql_lock(lock_name)
            return

        acquired = _NON_MYSQL_PLATFORM_CLAIM_LOCK.acquire(timeout=cls.PLATFORM_LOCK_TIMEOUT_SECONDS)
        try:
            yield acquired
        finally:
            if acquired:
                _NON_MYSQL_PLATFORM_CLAIM_LOCK.release()

    @staticmethod
    def eligible_condition(timeout_at):
        return (
                Q(status=TaskEnum.STAY_BEGIN.value)
                | Q(
            Q(push_time__lt=timeout_at) | Q(push_time__isnull=True),
            status=TaskEnum.PROCEED.value,
        )
        )

    @classmethod
    def valid_running_queryset(cls, timeout_at):
        return TestSuiteDetails.objects.filter(
            type=TestCaseTypeEnum.API.value,
            status=TaskEnum.PROCEED.value,
            push_time__gte=timeout_at,
        )

    @classmethod
    def candidate_suite_ids(cls, timeout_at, max_attempts: int | None = None):
        max_attempts = (
            max_attempts
            if max_attempts is not None
            else SystemConfigService.get_test_suite_timeout_max_attempts()
        )
        candidate_details = TestSuiteDetails.objects.filter(
            retry__lt=max_attempts,
            type=TestCaseTypeEnum.API.value,
        )
        pending_suites = (
            candidate_details.filter(status=TaskEnum.STAY_BEGIN.value)
            .order_by()
            .values('test_suite_id', 'test_env')
            .annotate(
                first_created_at=Min('create_time'),
                environment_priority=TestCenterQuerySelector.execution_environment_priority(),
            )
        )
        timed_out_suites = (
            candidate_details.filter(
                Q(push_time__lt=timeout_at) | Q(push_time__isnull=True),
                status=TaskEnum.PROCEED.value,
            )
            .order_by()
            .values('test_suite_id', 'test_env')
            .annotate(
                first_created_at=Min('create_time'),
                environment_priority=TestCenterQuerySelector.execution_environment_priority(),
            )
        )

        # 从活跃明细反向收集候选测试套，避免为每一条历史测试套执行相关子查询。
        suite_priorities = {}
        for candidate_queryset in (pending_suites, timed_out_suites):
            for candidate in candidate_queryset:
                test_suite_id = candidate['test_suite_id']
                priority = (candidate['environment_priority'], candidate['first_created_at'])
                previous = suite_priorities.get(test_suite_id)
                if previous is None or priority < previous:
                    suite_priorities[test_suite_id] = priority

        return sorted(suite_priorities, key=suite_priorities.__getitem__)

    @classmethod
    def claim(cls, lease_seconds: int | None = None) -> ExecutionCaseCommand | None:
        if lease_seconds is None:
            lease_seconds = SystemConfigService.get_executor_execution_timeout_seconds(
                ExecutorTaskTypeEnum.API_EXECUTION.value,
                default_seconds=60 * 60,
            )
        max_attempts = SystemConfigService.get_test_suite_timeout_max_attempts()
        platform_limit = ApiConcurrencyService.platform_limit()
        with cls.platform_claim_lock() as lock_acquired:
            if not lock_acquired:
                return None
            now = timezone.now()
            timeout_at = now - timedelta(seconds=lease_seconds)
            return cls.claim_with_platform_lock(
                now,
                timeout_at,
                platform_limit,
                max_attempts=max_attempts,
            )

    @classmethod
    def claim_with_platform_lock(
            cls,
            now,
            timeout_at,
            platform_limit: int,
            *,
            max_attempts: int,
    ) -> ExecutionCaseCommand | None:
        if cls.valid_running_queryset(timeout_at).count() >= platform_limit:
            return None

        for test_suite_id in cls.candidate_suite_ids(timeout_at, max_attempts):
            with transaction.atomic():
                test_suite = TestSuite.objects.select_for_update().get(id=test_suite_id)
                suite_limit = ApiConcurrencyService.clamp_snapshot_limit(
                    test_suite.api_concurrency_limit,
                    platform_limit,
                )
                running_count = cls.valid_running_queryset(timeout_at).filter(
                    test_suite_id=test_suite.id,
                ).count()
                if running_count >= suite_limit:
                    continue
                if cls.valid_running_queryset(timeout_at).count() >= platform_limit:
                    return None

                detail = (
                    TestSuiteDetails.objects.filter(
                        cls.eligible_condition(timeout_at),
                        test_suite_id=test_suite.id,
                        retry__lt=max_attempts,
                        type=TestCaseTypeEnum.API.value,
                    )
                    .order_by('create_time')
                    .first()
                )
                if not detail:
                    continue
                detail.test_suite = test_suite
                claim_error_message = detail.error_message
                if detail.status == TaskEnum.PROCEED.value:
                    current_attempt = max(1, int(detail.retry or 0))
                    claim_error_message = TestSuiteTimeoutRecoveryService.retry_message(
                        detail.type,
                        max(1, int((now - timeout_at).total_seconds() // 60)),
                        current_attempt,
                        min(current_attempt + 1, max_attempts),
                        max_attempts,
                    )
                if detail.api_case_revision_id:
                    selection = ApiCaseRevisionService.resolve_revision(
                        detail.case_id,
                        detail.api_case_revision_id,
                        release_id=detail.api_case_release_id,
                    )
                elif not test_suite.tasks_id:
                    # 手动批量执行的编辑态不绑定修订，领取时直接读取当前编辑态。
                    selection = None
                else:
                    version_policy = ApiCaseTaskBindingService.report_detail_version_policy(detail)
                    selection = ApiCaseTaskBindingService.resolve_execution_selection(
                        detail.case_id,
                        version_policy,
                    )
                updated = TestSuiteDetails.objects.filter(
                    cls.eligible_condition(timeout_at),
                    id=detail.id,
                    retry__lt=max_attempts,
                    type=TestCaseTypeEnum.API.value,
                ).update(
                    status=TaskEnum.PROCEED.value,
                    retry=F('retry') + 1,
                    push_time=now,
                    error_message=claim_error_message,
                    api_case_revision_id=selection.case_revision_id if selection else None,
                    api_case_release_id=selection.case_release_id if selection else None,
                    config_checksum=selection.checksum if selection else None,
                    update_time=now,
                )
                if updated != 1:
                    continue
                TestSuite.objects.filter(id=test_suite.id).update(
                    status=TaskEnum.PROCEED.value,
                    update_time=now,
                )
                return ExecutionCaseCommand(
                    test_suite_details=detail.id,
                    test_suite=detail.test_suite_id,
                    case_id=detail.case_id,
                    case_name=detail.case_name,
                    test_env=detail.test_env,
                    user_id=test_suite.user_id,
                    tasks_id=test_suite.tasks_id,
                    parametrize=detail.parametrize,
                    case_revision_id=selection.case_revision_id if selection else None,
                    case_release_id=selection.case_release_id if selection else None,
                    config_checksum=selection.checksum if selection else None,
                )
        return None
