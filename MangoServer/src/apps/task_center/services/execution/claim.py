import threading
from dataclasses import replace
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256

from django.db import connection, transaction
from django.db.models import Count, F, Max, Min, Q
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.schemas.execution import ApiWorkerClaimOwner, ExecutionCaseCommand
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.reporting.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock

_NON_MYSQL_PLATFORM_CLAIM_LOCK = threading.Lock()


class ApiTaskClaimService:
    PLATFORM_LOCK_PREFIX = 'mango:api:claim'
    PLATFORM_LOCK_TIMEOUT_SECONDS = 1

    @staticmethod
    def renew_wait(case_model, lease_seconds):
        now = timezone.now()
        # 只续约仍有效的同一轮领取，不能在排队时复活超时/重试/已停止的 Case。
        return TestSuiteDetails.objects.filter(
            id=case_model.test_suite_details, retry=case_model.attempt,
            status=TaskEnum.PROCEED.value,
            push_time__gte=now - timedelta(seconds=lease_seconds),
        ).filter(ApiTaskClaimService.not_blocked_condition()).exclude(
            test_suite__status=TaskEnum.STOPPED.value).update(push_time=now) == 1

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
    def not_blocked_condition():
        key = 'summary_data__meta__execution_control__phase'
        return Q(summary_data__isnull=True) | Q(**{f'{key}__isnull': True}) | ~Q(**{
            key: ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value})

    @staticmethod
    def eligible_condition(timeout_at):
        return (
                Q(status=TaskEnum.STAY_BEGIN.value)
                | Q(
            Q(push_time__lt=timeout_at) | Q(push_time__isnull=True),
            status=TaskEnum.PROCEED.value,
        ) & ApiTaskClaimService.not_blocked_condition()
        )

    @classmethod
    def valid_running_queryset(cls, timeout_at):
        suspended = cls.suspended_queryset(timeout_at).values('id')
        return TestSuiteDetails.objects.filter(
            type=TestCaseTypeEnum.API.value,
            status=TaskEnum.PROCEED.value,
            push_time__gte=timeout_at,
        ).filter(cls.not_blocked_condition()).exclude(id__in=suspended).exclude(
            test_suite__status=TaskEnum.STOPPED.value)

    @classmethod
    def suspended_queryset(cls, timeout_at):
        return TestSuiteDetails.objects.filter(type=TestCaseTypeEnum.API.value,
            status=TaskEnum.PROCEED.value, push_time__gte=timeout_at,
            summary_data__meta__resource_wait__suspended=True,
            summary_data__meta__resource_wait__attempt=F('retry'),
            summary_data__meta__resource_wait__process_token=F('summary_data__meta__worker_owner__process_token'),
        ).filter(cls.not_blocked_condition()).exclude(test_suite__status=TaskEnum.STOPPED.value)

    @staticmethod
    def not_blocked_detail(detail):
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        return not TestSuiteInfrastructureService.is_blocked(detail.summary_data)

    @classmethod
    def candidate_suite_ids(cls, timeout_at, max_attempts: int | None = None):
        max_attempts = (
            max_attempts
            if max_attempts is not None
            else SystemConfigService.get_test_suite_timeout_max_attempts()
        )
        suspended_ids = cls.suspended_queryset(timeout_at).values('id')
        candidate_details = TestSuiteDetails.objects.filter(
            Q(retry__lt=max_attempts) | Q(id__in=suspended_ids), type=TestCaseTypeEnum.API.value,
        ).filter(cls.not_blocked_condition()).exclude(test_suite__status=TaskEnum.STOPPED.value)
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
        suspended_suites = candidate_details.filter(id__in=suspended_ids).order_by().values(
            'test_suite_id', 'test_env').annotate(first_created_at=Min('create_time'),
                environment_priority=TestCenterQuerySelector.execution_environment_priority())
        for candidate_queryset in (pending_suites, timed_out_suites, suspended_suites):
            for candidate in candidate_queryset:
                test_suite_id = candidate['test_suite_id']
                priority = (candidate['environment_priority'], candidate['first_created_at'])
                previous = suite_priorities.get(test_suite_id)
                if previous is None or priority < previous:
                    suite_priorities[test_suite_id] = priority

        # 已领取的历史大报告不能始终排在从未获得执行位的新报告之前。
        # 仅改变后续领取顺序，不中断在途 Case、不重放未知请求，也不扩大并发。
        last_claims = {row['test_suite_id']: row['last_dispatch'] or (
            row['last_claim'].isoformat() if row['last_claim'] else None)
            for row in TestSuiteDetails.objects.filter(test_suite_id__in=suite_priorities).order_by()
            .values('test_suite_id').annotate(last_dispatch=Max('summary_data__meta__dispatch_started_at'),
                                             last_claim=Max('push_time'))}
        return sorted(suite_priorities, key=lambda suite_id: (
            suite_priorities[suite_id][0], last_claims.get(suite_id) is not None,
            last_claims.get(suite_id) or suite_priorities[suite_id][1].isoformat(),
            suite_priorities[suite_id][1], suite_id))

    @classmethod
    def claim(cls, lease_seconds: int | None = None, *, worker_owner=None) -> ExecutionCaseCommand | None:
        if worker_owner is not None:
            worker_owner = ApiWorkerClaimOwner.model_validate(worker_owner).model_dump()
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
                worker_owner=worker_owner,
            )

    @classmethod
    def claim_with_platform_lock(
            cls,
            now,
            timeout_at,
            platform_limit: int,
            *,
            max_attempts: int,
            worker_owner=None,
    ) -> ExecutionCaseCommand | None:
        counts = dict(cls.valid_running_queryset(timeout_at).order_by().values('test_suite_id')
                      .annotate(total=Count('id')).values_list('test_suite_id', 'total'))
        if sum(counts.values()) >= platform_limit:
            return None

        for test_suite_id in cls.candidate_suite_ids(timeout_at, max_attempts):
            with transaction.atomic():
                test_suite = TestSuite.objects.select_for_update().get(id=test_suite_id)
                suite_limit = ApiConcurrencyService.clamp_snapshot_limit(
                    test_suite.api_concurrency_limit,
                    platform_limit,
                )
                running_count = counts.get(test_suite.id, 0)
                if running_count >= suite_limit:
                    continue

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
                if detail.status == TaskEnum.PROCEED.value:
                    from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
                    TestSuiteInfrastructureService.block(detail.id, int(detail.retry or 0), [])
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
                    if detail.api_case_release_id is None:
                        selection = replace(selection, case_release_id=None)
                elif not test_suite.tasks_id:
                    # 手动批量执行的编辑态不绑定修订，领取时直接读取当前编辑态。
                    selection = None
                else:
                    version_policy = ApiCaseTaskBindingService.report_detail_version_policy(detail)
                    selection = ApiCaseTaskBindingService.resolve_execution_selection(
                        detail.case_id,
                        version_policy,
                    )
                from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
                children, meta = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
                meta = {**(meta or {}), 'dispatch_started_at': now.isoformat()}
                meta.pop('resource_wait', None)
                if worker_owner is not None:
                    meta['worker_owner'] = dict(worker_owner)
                summary_updates = {'summary_data': TestSuiteExecutionResultService.pack_summary_data(children, meta)}
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
                    **summary_updates,
                )
                if updated != 1:
                    continue
                TestSuite.objects.filter(id=test_suite.id).update(
                    status=TaskEnum.PROCEED.value,
                    update_time=now,
                )
                return ExecutionCaseCommand(
                    attempt=int(detail.retry or 0) + 1,
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
