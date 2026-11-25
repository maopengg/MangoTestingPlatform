from django.db.models import Q
from mangotools.enums import TaskEnum

from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.models import TestSuiteDetails, ExecutionResult
from src.apps.test_center.enums import TestCaseTypeEnum


class ReportRecoverySelector:
    @staticmethod
    def candidates(limit=100):
        return list(TestSuiteDetails.objects.filter(
            Q(status=TaskEnum.PROCEED.value,
              summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.AUTOMATIC_RECOVERY.value)
            | Q(status=TaskEnum.FAIL.value,
                summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.RECOVERY_FAILED.value,
                summary_data__meta__execution_control__exception_recorded=False),
            summary_data__meta__execution_control__version=2,
            type=TestCaseTypeEnum.API.value,
            test_suite__retained_summary__isnull=True,
        ).exclude(test_suite__status=TaskEnum.STOPPED.value).order_by('update_time', 'id').values_list('id', flat=True)[:limit])

    @staticmethod
    def completed_result(detail, started_at):
        queryset = ExecutionResult.objects.filter(
            source_type='report', test_suite_detail_id=detail.id, test_suite_id=detail.test_suite_id,
            status__in=(TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value),
            create_time__gte=started_at,
        )
        summary = detail.summary_data if isinstance(detail.summary_data, dict) else {}
        result_id = (summary.get('meta') or {}).get('execution_control', {}).get('result_id')
        if result_id is not None:
            queryset = queryset.filter(id=result_id)
        return queryset.order_by('-id').first()
