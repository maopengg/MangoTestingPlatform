from django.db.models import Q, Max, F, Case, When, Value, IntegerField, Count
from mangotools.enums import TaskEnum

from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum


class ReportInfrastructureSelector:
    @staticmethod
    def status_counts(queryset):
        legacy = Q(summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value)
        rows = queryset.annotate(display_status=Case(
            When(Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value) | legacy, then=Value(TaskEnum.FAIL.value)),
            default=F('status'), output_field=IntegerField(),
        )).values('display_status').annotate(total=Count('id'))
        counts = {row['display_status']: row['total'] for row in rows}
        return {**{key: counts.get(status.value, 0) for key, status in (
            ('fail', TaskEnum.FAIL), ('success', TaskEnum.SUCCESS), ('stay_begin', TaskEnum.STAY_BEGIN),
            ('proceed', TaskEnum.PROCEED), ('stopped', TaskEnum.STOPPED), ('warning', TaskEnum.WARNING))}, 'blocked': 0}

    @staticmethod
    def detail_ids(suite_id):
        return TestSuiteDetails.objects.filter(test_suite_id=suite_id).values('id')

    @staticmethod
    def filter_status(queryset, status):
        legacy = Q(status=TaskEnum.FAIL.value,
            summary_data__meta__execution_control__phase__isnull=False,
            summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value)
        if str(status) == str(TaskEnum.INFRASTRUCTURE_BLOCKED.value):
            return queryset.filter(Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value) | legacy)
        if str(status) == str(TaskEnum.FAIL.value):
            return queryset.filter(Q(status__in=(TaskEnum.FAIL.value, TaskEnum.INFRASTRUCTURE_BLOCKED.value)) | legacy)
        return queryset.filter(status=status)

    @staticmethod
    def report(suite_id):
        suite = TestSuite.objects.select_related('project_product__project', 'tasks', 'user').get(id=suite_id)
        if suite.tasks_id:
            return TestSuite.objects.filter(tasks_id=suite.tasks_id,
                project_product_id=suite.project_product_id, test_env=suite.test_env,
            ).select_related('project_product__project', 'tasks', 'user').order_by('-create_time', '-id').first()
        return suite

    @staticmethod
    def details(suite_id):
        return TestSuiteDetails.objects.filter(test_suite_id=suite_id).values(
            'id', 'case_id', 'type', 'status', 'is_excluded').annotate(
                infrastructure_phase=F('summary_data__meta__execution_control__phase'))

    @staticmethod
    def blocked_report_ids():
        ids = TestSuiteDetails.objects.filter(
            Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value) |
            Q(summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value),
            is_excluded=False,
        ).values('test_suite_id')
        scheduled = TestSuite.objects.filter(id__in=ids, tasks_id__isnull=False).values(
            'tasks_id', 'project_product_id', 'test_env').annotate(latest_id=Max('id'))
        yield from scheduled.values_list('latest_id', flat=True).iterator(chunk_size=200)
        yield from TestSuite.objects.filter(id__in=ids, tasks_id__isnull=True).values_list('id', flat=True).iterator(chunk_size=200)
