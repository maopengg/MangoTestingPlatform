from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStatus
from src.apps.auto_api.models import ApiCaseExecutionTrace, ApiCaseExecutionStep
from src.apps.auto_api.selectors.case_list_execution import ApiCaseListExecutionSelector
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum as Phase
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector


class ApiReportTraceStateSelector:
    @staticmethod
    def candidates(limit=100):
        open_steps = ApiCaseExecutionStep.objects.filter(status=ApiCaseTraceStatus.PROCEED).values('trace_id')
        traces = ApiCaseExecutionTrace.objects.filter(test_suite_detail_id__isnull=False,
            update_time__lt=timezone.now() - timedelta(minutes=2)).filter(
            Q(status=ApiCaseTraceStatus.PROCEED) | Q(id__in=open_steps))
        traces = ApiCaseListExecutionSelector.with_trace_status(traces).filter(report_detail_id__isnull=False)
        terminal = [TaskEnum.FAIL.value, TaskEnum.SUCCESS.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value]
        return list(TestCenterQuerySelector.test_suite_details().filter(
            id__in=traces.values('test_suite_detail_id'),
        ).filter(
            Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value)
            | Q(summary_data__meta__execution_control__phase=Phase.INFRASTRUCTURE_BLOCKED.value)
            | Q(status__in=terminal, summary_data__meta__execution_control__phase__isnull=True)
            | Q(summary_data__meta__execution_control__version=2,
                summary_data__meta__execution_control__owner_ended=True),
        ).order_by('update_time', 'id').values_list('id', flat=True)[:limit])
