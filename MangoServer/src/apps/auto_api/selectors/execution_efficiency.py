from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace
from django.db.models import Max, Q


class ApiExecutionEfficiencySelector:
    @staticmethod
    def latest_step_activity(owners, since):
        condition = Q()
        for owner in owners:
            if owner['started_at'] is not None:
                condition |= Q(test_suite_detail_id=owner['detail_id'], started_at__gte=owner['started_at'])
        if not condition:
            return {}
        # 每个执行项只看本次领取之后的最新 Trace，旧轮次的延迟收尾不能掩盖本轮停滞。
        current = {}
        for row in ApiCaseExecutionTrace.objects.filter(condition).order_by('-create_time', '-id').values(
                'id', 'test_suite_detail_id'):
            current.setdefault(row['test_suite_detail_id'], row['id'])
        by_trace = {trace_id: detail_id for detail_id, trace_id in current.items()}
        return {by_trace[row['trace_id']]: row['latest'] for row in ApiCaseExecutionStep.objects.filter(
            trace_id__in=by_trace, finished_at__gte=since).order_by().values('trace_id').annotate(
                latest=Max('finished_at'))}

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
