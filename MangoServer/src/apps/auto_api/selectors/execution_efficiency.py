from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace


class ApiExecutionEfficiencySelector:
    @staticmethod
    def traces(*, report_ids=None, detail_ids=None, limit=10001):
        queryset = ApiCaseExecutionTrace.objects.all()
        if report_ids is not None:
            queryset = queryset.filter(test_suite_id__in=report_ids)
        elif detail_ids is not None:
            queryset = queryset.filter(test_suite_detail_id__in=detail_ids)
        else:
            return []
        return list(queryset.order_by('id').values(
            'id', 'trace_id', 'test_suite_id', 'test_suite_detail_id', 'case_id', 'case_name',
            'status', 'started_at', 'finished_at', 'duration_ms',
        )[:limit])

    @staticmethod
    def steps(trace_ids, limit=50001, *, unfinished_only=False):
        queryset = ApiCaseExecutionStep.objects.filter(trace_id__in=trace_ids)
        if unfinished_only:
            queryset = queryset.filter(finished_at__isnull=True)
        return list(queryset.order_by('id').values(
            'id', 'trace_id', 'parent_step_id', 'step_type', 'step_name', 'status',
            'started_at', 'finished_at', 'duration_ms',
        )[:limit])
