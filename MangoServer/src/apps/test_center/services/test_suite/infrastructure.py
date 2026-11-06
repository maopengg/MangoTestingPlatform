from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.enums.case import ReportFailureReasonEnum
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.schemas.infrastructure import ReportInfrastructureBlock
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService


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
    def block(cls, detail_id, attempt, issues, *, snapshot=None, expected_push_time=None):
        suite_id = TestSuiteDetails.objects.filter(id=detail_id).values_list('test_suite_id', flat=True).get()
        suite = TestSuite.objects.select_for_update().get(id=suite_id)
        detail = TestSuiteDetails.objects.select_for_update().get(id=detail_id, test_suite_id=suite_id)
        if (detail.retry != attempt or detail.status != TaskEnum.PROCEED.value
                or suite.status == TaskEnum.STOPPED.value
                or (expected_push_time is not None and detail.push_time != expected_push_time)):
            return False
        control = ReportInfrastructureBlock(attempt=attempt, observed_at=timezone.now().isoformat(), issues=issues)
        if snapshot is not None:
            TestSuiteExecutionResultService.save_snapshot(detail, snapshot)
        children, meta = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
        detail.summary_data = {'children': children or [], 'meta': {**(meta or {}),
            'execution_control': control.model_dump(mode='json')}}
        reasons = list(dict.fromkeys(issue.message for issue in issues))
        detail.error_message = '本次回归未完成：' + '；'.join(reasons) if reasons else '执行已中断，平台未收到完整结果。请核查本次请求及清理状态，勿直接重复写入'
        detail.success = detail.fail = detail.warning = 0
        detail.failure_reason = (ReportFailureReasonEnum.PLATFORM.value if not issues or any(
            issue.origin == ReportFailureReasonEnum.PLATFORM for issue in issues) else ReportFailureReasonEnum.ENVIRONMENT.value)
        detail.failure_description = '；'.join(reasons) or detail.error_message
        detail.save(update_fields=['summary_data', 'error_message', 'success', 'fail', 'warning',
                                   'failure_reason', 'failure_description', 'update_time'])
        TestSuite.objects.filter(id=detail.test_suite_id).exclude(status=TaskEnum.STOPPED.value).update(
            status=TaskEnum.PROCEED.value, update_time=timezone.now())
        from src.common.logging import log
        log.system.warning('event=report_infrastructure_blocked detail_id=%s attempt=%s issue_codes=%s',
                           detail.id, attempt, [issue.code for issue in issues])
        return True
