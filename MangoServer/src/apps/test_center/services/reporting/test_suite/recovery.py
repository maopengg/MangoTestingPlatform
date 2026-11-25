from datetime import timedelta
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError
from mangotools.enums import TaskEnum

from src.apps.data_factory.exceptions import (
    DATASOURCE_POLICY_INVALID, DATASOURCE_AUDIT_REQUEST_CONFLICT, DATASOURCE_OPERATION_COST_EXCEEDED,
    DATA_FACTORY_CLEANUP_COORDINATION_FAILED, DATASOURCE_GOVERNOR_UNAVAILABLE,
    DATASOURCE_ADMISSION_TIMEOUT, DATASOURCE_AUDIT_UNAVAILABLE,
    DATASOURCE_RECONCILIATION_REQUIRED, DATASOURCE_SETTLEMENT_FAILED,
    DATASOURCE_AUDIT_COMPLETION_FAILED, DATASOURCE_AUDIT_RESULT_UNAVAILABLE,
    DATA_FACTORY_CLEANUP_IN_PROGRESS, DATA_FACTORY_CLEANUP_INTERRUPTED, DATA_FACTORY_CLEANUP_TIMEOUT,
)
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.test_center.enums.reporting import ReportRecoveryActionEnum as Action, ReportRecoveryCauseEnum as Cause, ReportExecutionPhaseEnum as Phase
from src.apps.test_center.enums.reporting import ReportRecoveryReasonEnum as Reason, ReportRecoveryOutcomeEnum as Outcome
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.exceptions import ReportResultRecoveryPending
from src.apps.test_center.schemas.infrastructure import ReportRecoveryControl
from src.apps.test_center.selectors.report_recovery import ReportRecoverySelector
from src.common.logging import log


class ReportRecoveryService:
    """只处理带新版结构化证据的执行；旧受阻记录不自动重置。"""

    @staticmethod
    def is_confirmed_code_bug(error):
        return isinstance(error, (AttributeError, TypeError, NameError, KeyError, IndexError,
                                  NotImplementedError, AssertionError))

    @staticmethod
    def decide(cause, issues):
        fatal = {DATASOURCE_POLICY_INVALID.code, DATASOURCE_AUDIT_REQUEST_CONFLICT.code,
                 DATASOURCE_OPERATION_COST_EXCEEDED.code, DATA_FACTORY_CLEANUP_COORDINATION_FAILED.code}
        transient = {DATASOURCE_GOVERNOR_UNAVAILABLE.code, DATASOURCE_ADMISSION_TIMEOUT.code,
                     DATASOURCE_AUDIT_UNAVAILABLE.code}
        recoverable = {DATASOURCE_RECONCILIATION_REQUIRED.code, DATASOURCE_SETTLEMENT_FAILED.code,
                       DATASOURCE_AUDIT_COMPLETION_FAILED.code, DATASOURCE_AUDIT_RESULT_UNAVAILABLE.code,
                       DATA_FACTORY_CLEANUP_IN_PROGRESS.code, DATA_FACTORY_CLEANUP_INTERRUPTED.code,
                       DATA_FACTORY_CLEANUP_TIMEOUT.code}
        if cause == Cause.CODE_BUG or any(issue.code in fatal or issue.code not in transient | recoverable for issue in issues):
            return Action.FAIL
        if issues:
            return Action.RETRY if all(issue.code in transient for issue in issues) else Action.RECOVER
        return Action.RETRY if cause == Cause.WORKER_REPLACED else Action.RECOVER

    @staticmethod
    def read(summary):
        meta = summary.get('meta') if isinstance(summary, dict) else None
        raw = meta.get('execution_control') if isinstance(meta, dict) else None
        if not isinstance(raw, dict) or raw.get('version') != 2:
            return None
        try:
            return ReportRecoveryControl.model_validate(raw)
        except ValidationError:
            return None

    @staticmethod
    def put(detail, control):
        summary = detail.summary_data if isinstance(detail.summary_data, dict) else {'children': detail.summary_data}
        detail.summary_data = {**summary, 'meta': {**(summary.get('meta') or {}),
            'execution_control': control.model_dump(mode='json')}}

    @classmethod
    def begin_locked(cls, suite, detail, issues, cause):
        now = timezone.now()
        control = ReportRecoveryControl(attempt=max(1, int(detail.retry or 0)), cause=cause,
            action=cls.decide(cause, issues), observed_at=now, next_check_at=now + timedelta(seconds=2),
            deadline_at=now + timedelta(minutes=SystemConfigService.get_test_suite_stuck_reset_minutes()),
            owner_ended=cause in (Cause.WORKER_REPLACED, Cause.TASK_UNREPORTED, Cause.DATASOURCE, Cause.CODE_BUG, Cause.RESULT_UNAVAILABLE),
            result_expected=cause == Cause.RESULT_UNAVAILABLE,
            issues=issues[:100])
        cls.put(detail, control)
        if control.action == Action.FAIL:
            cls.fail_locked(suite, detail, control, Reason.NON_RETRYABLE)
        else:
            detail.status = TaskEnum.PROCEED.value
            detail.save(update_fields=['status', 'summary_data', 'error_message', 'failure_reason',
                                       'failure_description', 'update_time'])
        return control

    @classmethod
    def record_failure_locked(cls, detail, control):
        if control.exception_recorded:
            return
        from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
        control.next_check_at = timezone.now() + timedelta(seconds=60)
        cls.put(detail, control)
        detail.save(update_fields=['summary_data', 'update_time'])
        try:
            # 登记和去重标记在同一业务事务内；失败时保存点回滚，留待定时补偿。
            with transaction.atomic():
                SystemErrorEventService.record_report_recovery_failure(
                    suite_id=detail.test_suite_id, detail_id=detail.id, attempt=control.attempt,
                    cause=control.cause, reason=control.reason.value if control.reason else '', codes=[issue.code for issue in control.issues])
                control.exception_recorded = True
                cls.put(detail, control)
                detail.save(update_fields=['summary_data'])
        except Exception:
            control.exception_recorded = False
            cls.put(detail, control)
            log.system.warning('自动恢复失败的系统异常登记待补偿：detail=%s attempt=%s', detail.id, control.attempt)

    @classmethod
    def fail_locked(cls, suite, detail, control, reason):
        control.phase, control.reason = Phase.RECOVERY_FAILED, reason
        detail.status = TaskEnum.FAIL.value
        total = max(int(detail.case_sum or 0), 1)
        detail.success = min(max(int(detail.success or 0), 0), total - 1)
        detail.warning = min(max(int(detail.warning or 0), 0), total - detail.success - 1)
        detail.fail = total - detail.success - detail.warning
        detail.error_message = '测试执行未完整完成，自动恢复已停止。请查看失败原因、执行记录及系统异常记录。'
        cls.put(detail, control)
        detail.save(update_fields=['status', 'success', 'fail', 'warning', 'summary_data', 'error_message',
                                   'failure_reason', 'failure_description', 'update_time'])
        cls.record_failure_locked(detail, control)
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        TestSuiteInfrastructureService._finish_suite(suite)

    @staticmethod
    def owner_ended(detail, control):
        if control.owner_ended:
            return True
        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
        meta = (detail.summary_data or {}).get('meta') or {}
        owner = meta.get('worker_owner') or {}
        return ApiWorkerRecoveryService.execution_owner_replaced(owner.get('worker_name'), owner, detail.push_time)

    @staticmethod
    def resources_ready(detail, control):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        return (DatasourceInfrastructureService.review_ready(detail)
                and not ApiResourceCleanupSelector.has_unfinished_for_attempt(
                    detail.id, (detail.summary_data or {}).get('meta', {}).get('dispatch_started_at') or detail.push_time))

    @staticmethod
    def restore_result(detail):
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        from src.apps.test_center.services.reporting.testcounter import TestCounter
        meta = (detail.summary_data or {}).get('meta') or {}
        started = meta.get('dispatch_started_at') or detail.push_time
        control = ReportRecoveryService.read(detail.summary_data)
        if not started:
            if control and control.result_expected:
                raise ReportResultRecoveryPending
            return None
        saved = ReportRecoverySelector.completed_result(detail, started)
        if saved is None:
            if control and control.result_expected:
                raise ReportResultRecoveryPending
            return None
        data = ExecutionResultService.load_result_data(saved)
        if data is None:
            raise ReportResultRecoveryPending
        checksum = getattr(saved, 'result_checksum', None)
        if checksum and ExecutionResultService.calc_result_checksum(data) != checksum:
            raise ReportResultRecoveryPending
        if Results.is_api_snapshot(data) or (isinstance(data, dict) and
                (data.get('infrastructure_blocked') or data.get('execution_finalized') is False)):
            if control and control.result_expected:
                raise ReportResultRecoveryPending
            return None
        # 原结果已持久化且为终态，仅恢复计数与摘要，不再次发出请求。
        probe = SimpleNamespace(status=saved.status, summary_data=detail.summary_data, case_sum=detail.case_sum)
        with_results = Results.normalize_detail_result_data(detail, data)
        if not isinstance(with_results, list):
            raise ReportResultRecoveryPending
        counts = {'success': 0, 'fail': 0, 'warning': 0}
        for row in with_results:
            status = row.get('status') if isinstance(row, dict) else TaskEnum.FAIL.value
            key = 'success' if status == TaskEnum.SUCCESS.value else 'warning' if status == TaskEnum.WARNING.value else 'fail'
            counts[key] += 1
        if with_results:
            TestCounter.fill_missing_warnings(counts, max(int(detail.case_sum or 0), 1))
        else:
            counts['fail'] = max(int(detail.case_sum or 0), 1)
        from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService
        status = TaskEnum.FAIL.value if counts['fail'] else TaskEnum.WARNING.value if counts['warning'] else saved.status
        return status, ApiReportCountingService.counter(probe, counts), Results.build_summary_data(detail, with_results)

    @classmethod
    def process_due(cls, limit=100):
        processed = 0
        for identity in ReportRecoverySelector.candidates(limit):
            try:
                processed += bool(cls.process_one(identity))
            except Exception as error:
                log.system.error('报告自动恢复检查失败，保留原执行责任：detail=%s type=%s', identity, type(error).__name__)
        return processed

    @classmethod
    @transaction.atomic
    def note_owner_ended(cls, detail_id, attempt, *, code_bug=False, result_expected=False):
        suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).first()
        suite = TestSuite.objects.select_for_update().filter(id=suite_id).first()
        detail = TestSuiteDetails.objects.select_for_update().filter(id=detail_id, retry=attempt).first()
        if (detail is None or suite is None or suite.status == TaskEnum.STOPPED.value
                or suite.retained_summary or detail.status != TaskEnum.PROCEED.value):
            return False
        control = cls.read(detail.summary_data)
        if control is None or control.attempt != attempt or control.phase != Phase.AUTOMATIC_RECOVERY:
            return False
        control.owner_ended = True
        control.result_expected = control.result_expected or result_expected
        control.next_check_at = timezone.now() + timedelta(seconds=2)
        if code_bug:
            control.cause, control.action = Cause.CODE_BUG, Action.FAIL
            cls.fail_locked(suite, detail, control, Reason.CODE_BUG)
        else:
            cls.put(detail, control)
            detail.save(update_fields=['summary_data', 'update_time'])
        return True

    @classmethod
    def process_one(cls, detail_id):
        # 先用短事务抢占检查轮次，不在报告行锁内访问对象存储或被测数据源。
        now = timezone.now()
        with transaction.atomic():
            suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).first()
            suite = TestSuite.objects.select_for_update().filter(id=suite_id).first()
            detail = TestSuiteDetails.objects.select_for_update().filter(id=detail_id, test_suite_id=suite_id).first()
            if suite is None or detail is None or suite.status == TaskEnum.STOPPED.value or suite.retained_summary:
                return False
            control = cls.read(detail.summary_data)
            if control is None:
                meta = detail.summary_data.get('meta') if isinstance(detail.summary_data, dict) else None
                raw = meta.get('execution_control') if isinstance(meta, dict) else None
                if isinstance(raw, dict) and raw.get('version') == 2:
                    invalid = ReportRecoveryControl(attempt=max(1, detail.retry), cause=Cause.CODE_BUG,
                        action=Action.FAIL, observed_at=now, next_check_at=now, deadline_at=now)
                    cls.fail_locked(suite, detail, invalid, Reason.INVALID_CONTROL)
                    return True
                return False
            if control.attempt != detail.retry:
                return False
            if control.phase == Phase.RECOVERY_FAILED:
                if control.next_check_at <= now:
                    cls.record_failure_locked(detail, control)
                return False
            if (control.phase != Phase.AUTOMATIC_RECOVERY or detail.status != TaskEnum.PROCEED.value
                    or control.next_check_at > now):
                return False
            if now >= control.deadline_at:
                cls.fail_locked(suite, detail, control, Reason.DEADLINE_EXHAUSTED)
                return True
            control.checks += 1
            check = control.checks
            control.next_check_at = now + timedelta(seconds=60)
            cls.put(detail, control)
            detail.save(update_fields=['summary_data', 'update_time'])
        ended, ready, restored, internal_error, result_pending = False, False, None, False, False
        try:
            ended = cls.owner_ended(detail, control)
            if ended:
                try:
                    restored = cls.restore_result(detail)
                except ReportResultRecoveryPending:
                    result_pending = True
            if ended:
                from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
                TestSuiteInfrastructureService.close_interrupted_trace(detail)
                from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
                from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupService
                started = (detail.summary_data or {}).get('meta', {}).get('dispatch_started_at') or detail.push_time
                for record in ApiResourceCleanupSelector.pending_for_attempt(detail.id, started):
                    ApiResourceCleanupService.cleanup(record)
                ready = cls.resources_ready(detail, control)
        except Exception as error:
            from src.common.exceptions.normalization import normalize_expected_exception
            internal_error = cls.is_confirmed_code_bug(error) and normalize_expected_exception(error) is None
            log.system.error('报告恢复原执行未完成：detail=%s attempt=%s type=%s', detail_id, control.attempt, type(error).__name__)
        with transaction.atomic():
            suite = TestSuite.objects.select_for_update().get(id=suite_id)
            current = TestSuiteDetails.objects.select_for_update().get(id=detail_id)
            latest = cls.read(current.summary_data)
            if (suite.status == TaskEnum.STOPPED.value or current.status != TaskEnum.PROCEED.value
                    or suite.retained_summary or current.retry != control.attempt
                    or latest is None or latest.attempt != control.attempt or latest.checks != check
                    or latest.phase != Phase.AUTOMATIC_RECOVERY):
                return False
            latest.owner_ended = ended
            if result_pending:
                latest.result_expected = True
                latest.action, latest.reason = Action.RECOVER, Reason.RESULT_UNAVAILABLE
            if internal_error:
                latest.cause, latest.action = Cause.CODE_BUG, Action.FAIL
                cls.fail_locked(suite, current, latest, Reason.INTERNAL_ERROR)
                return True
            if restored is not None and ready:
                status, counts, children = restored
                current.status = status
                for key, value in counts.items():
                    setattr(current, key, value)
                meta = dict((current.summary_data or {}).get('meta') or {})
                meta.pop('execution_control', None)
                meta['recovery_history'] = cls.history(current, latest, Outcome.RESULT_RESTORED)
                current.summary_data = {'children': children, 'meta': meta}
                current.error_message = None if status == TaskEnum.SUCCESS.value else current.error_message
                current.save(update_fields=['status', 'success', 'fail', 'warning', 'summary_data', 'error_message', 'update_time'])
                TestSuiteInfrastructureService._finish_suite(suite)
                return True
            if timezone.now() >= latest.deadline_at:
                cls.fail_locked(suite, current, latest, Reason.DEADLINE_EXHAUSTED)
                return True
            if latest.result_expected:
                cls.put(current, latest)
                current.save(update_fields=['summary_data', 'update_time'])
                return False
            if ready and current.retry < SystemConfigService.get_test_suite_timeout_max_attempts():
                from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService
                empty = ApiReportCountingService.empty_summary(current) or {'children': None, 'meta': {}}
                empty.setdefault('meta', {})['recovery_history'] = cls.history(current, latest, Outcome.RETRY_QUEUED)
                current.summary_data = empty
                current.status, current.push_time, current.error_message = TaskEnum.STAY_BEGIN.value, None, None
                current.success = current.fail = current.warning = 0
                current.save(update_fields=['status', 'push_time', 'summary_data', 'error_message', 'success', 'fail', 'warning', 'update_time'])
                # retry 不归零，领取时仍由原队列原子递增。
                return True
            if ready:
                cls.fail_locked(suite, current, latest, Reason.RETRY_EXHAUSTED)
                return True
            cls.put(current, latest)
            current.save(update_fields=['summary_data', 'update_time'])
            return False

    @staticmethod
    def history(detail, control, outcome):
        old = (detail.summary_data or {}).get('meta', {}).get('recovery_history') or []
        return [*old[-10:], {'attempt': control.attempt, 'cause': control.cause.value,
                'action': control.action.value, 'outcome': outcome.value, 'observed_at': control.observed_at.isoformat(),
                'finished_at': timezone.now().isoformat()}]
