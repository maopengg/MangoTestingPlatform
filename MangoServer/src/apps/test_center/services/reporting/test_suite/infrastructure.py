from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from mangotools.enums import TaskEnum

from src.apps.test_center.enums.case import ReportFailureReasonEnum
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.schemas.infrastructure import ReportInfrastructureBlock
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService


class TestSuiteInfrastructureService:
    @staticmethod
    def blocked_suites(suite_ids):
        return TestSuiteDetails.objects.filter(test_suite_id__in=suite_ids,
            summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value)

    @staticmethod
    def is_blocked(summary):
        if not isinstance(summary, dict):
            return False
        meta = summary.get('meta')
        control = meta.get('execution_control') if isinstance(meta, dict) else None
        return isinstance(control, dict) and control.get('phase') == ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value

    @classmethod
    def has_live_details(cls, suite_id):
        # 用 ID 子查询排除阻塞项，保留历史 NULL/空 JSON 的正常待执行项。
        blocked_ids = cls.blocked_suites([suite_id]).values('id')
        return TestSuiteDetails.objects.filter(
            test_suite_id=suite_id,
            status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value],
        ).exclude(id__in=blocked_ids).exists()

    @classmethod
    @transaction.atomic
    def block(cls, detail_id, attempt, issues, *, snapshot=None, expected_push_time=None, interruption_reason=None):
        suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).get()
        suite = TestSuite.objects.select_for_update().get(id=suite_id)
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail_id, test_suite_id=suite_id)
        if (detail.retry != attempt or detail.status != TaskEnum.PROCEED.value
                or suite.status == TaskEnum.STOPPED.value
                or (expected_push_time is not None and detail.push_time != expected_push_time)):
            return False
        control = ReportInfrastructureBlock(attempt=attempt, observed_at=timezone.now().isoformat(), issues=issues)
        detail.status = TaskEnum.INFRASTRUCTURE_BLOCKED.value
        if snapshot is not None:
            try:
                with transaction.atomic():
                    TestSuiteExecutionResultService.save_snapshot(detail, snapshot)
            except Exception:
                from src.common.logging import log
                log.system.exception('平台受阻快照保存失败，保留受阻控制记录：detail=%s', detail.id)
        children, meta = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
        detail.summary_data = {'children': children or [], 'meta': {**(meta or {}),
            'execution_control': control.model_dump(mode='json')}}
        reasons = list(dict.fromkeys(issue.message for issue in issues))
        if interruption_reason:
            reasons.insert(0, interruption_reason)
        detail.error_message = '本次回归未完成：' + '；'.join(reasons) if reasons else '执行已中断，平台未收到完整结果。请核查本次请求及清理状态，勿直接重复写入'
        detail.failure_reason = (ReportFailureReasonEnum.PLATFORM.value if not issues or any(
            issue.origin == ReportFailureReasonEnum.PLATFORM for issue in issues) else ReportFailureReasonEnum.ENVIRONMENT.value)
        detail.failure_description = '；'.join(reasons) or detail.error_message
        detail.status = TaskEnum.INFRASTRUCTURE_BLOCKED.value
        detail.save(update_fields=['status', 'summary_data', 'error_message', 'success', 'fail', 'warning',
                                   'failure_reason', 'failure_description', 'update_time'])
        cls.close_interrupted_trace(detail)
        cls._finish_suite(suite)
        transaction.on_commit(lambda: cls.sync_todos(suite.id))
        from src.common.logging import log
        log.system.warning('event=report_infrastructure_blocked detail_id=%s attempt=%s issue_codes=%s',
                           detail.id, attempt, [issue.code for issue in issues])
        return True

    @staticmethod
    def close_interrupted_trace(detail):
        from src.apps.test_center.enums import TestCaseTypeEnum
        if detail.type == TestCaseTypeEnum.API.value:
            from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder
            _, meta = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
            # push_time 在等待清理时会续租，不能用它排除本轮较早开始的 Trace。
            try:
                dispatched_at = parse_datetime(str((meta or {}).get('dispatch_started_at') or ''))
            except ValueError:
                dispatched_at = None
            ApiCaseExecutionTraceRecorder.interrupt_report_attempt(
                detail.id, dispatched_at or detail.push_time, detail.error_message,
                detail.summary_data['meta']['execution_control'],
            )

    @staticmethod
    def _finish_suite(suite):
        # 运行状态与恢复许可分离：FAIL 表示执行未完成，不代表业务断言失败。
        if suite.status == TaskEnum.STOPPED.value or suite.retained_summary is not None:
            return
        statuses = set(TestSuiteDetails.objects.filter(test_suite_id=suite.id).values_list('status', flat=True))
        if statuses.intersection((TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)):
            return
        suite.status = (TaskEnum.FAIL.value if TaskEnum.FAIL.value in statuses or TestSuiteDetails.objects.filter(
                            test_suite_id=suite.id, is_excluded=False, fail__gt=0).exists()
                        else TaskEnum.INFRASTRUCTURE_BLOCKED.value)
        suite.save(update_fields=['status', 'update_time'])
        transaction.on_commit(lambda: TestSuiteInfrastructureService.finish_notice(suite.id))

    @staticmethod
    def finish_notice(suite_id):
        from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
        from src.common.logging import log
        try:
            SendNotice(suite_id).send_test_suite()
        except Exception:
            log.system.exception('平台受阻报告通知收口失败：report=%s', suite_id)

    @staticmethod
    def sync_todos(suite_id):
        from src.apps.task_center.services.workbench.report_infrastructure import ReportInfrastructureTodoService
        from src.common.logging import log
        try:
            ReportInfrastructureTodoService.sync(suite_id)
        except Exception:
            log.system.exception('报告受阻待办同步失败，保留报告并等待定时补偿：report=%s', suite_id)

    @classmethod
    def repair_legacy_blocks(cls, limit=200):
        ids = list(TestSuiteDetails.objects.filter(
            status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value],
            summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value,
            test_suite__retained_summary__isnull=True,
        ).exclude(test_suite__status=TaskEnum.STOPPED.value).order_by('id').values_list('id', flat=True)[:limit])
        return sum(cls.finish_legacy_block(detail_id) for detail_id in ids)

    @classmethod
    @transaction.atomic
    def finish_legacy_block(cls, detail_id):
        suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).first()
        if suite_id is None:
            return False
        suite = TestSuite.objects.select_for_update().get(id=suite_id)
        detail = TestSuiteDetails.objects.select_for_update().filter(id=detail_id, test_suite_id=suite_id).first()
        if (detail is None or suite.status == TaskEnum.STOPPED.value or suite.retained_summary is not None
                or detail.status not in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)
                or not cls.is_blocked(detail.summary_data)):
            return False
        # 不改执行次数、快照、复核许可或清理责任；更不重新领取原请求。
        detail.status = TaskEnum.INFRASTRUCTURE_BLOCKED.value
        detail.save(update_fields=['status'])
        cls.close_interrupted_trace(detail)
        cls._finish_suite(suite)
        return True
