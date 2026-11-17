from django.db.models import BooleanField, Case, ExpressionWrapper, F, IntegerField, Max, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce, Greatest
from mangotools.enums import TaskEnum

from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.models import TestSuiteDetails


class _ReportStatusReference(ExpressionWrapper):
    def get_group_by_cols(self):
        # 同一相关子查询内，外层报告状态是常量，不参与明细分组。
        return []


class ReportConclusionSelector:
    """与 TestSuiteSummaryService 的有效结果优先级一致，在分页前筛选。"""

    @staticmethod
    def with_conclusion(queryset):
        blocked = Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value) | Q(
            summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value)
        details = TestSuiteDetails.objects.filter(test_suite_id=OuterRef('pk')).order_by().alias(
            _raw_status=_ReportStatusReference(OuterRef('status'), output_field=IntegerField()),
            _size=Greatest(Coalesce('case_sum', 0), 1),
            _success=Greatest(Coalesce('success', 0), 0),
            _fail=Greatest(Coalesce('fail', 0), 0),
            _warning=Greatest(Coalesce('warning', 0), 0),
            _blocked=Case(When(blocked, then=Value(True)), default=Value(False), output_field=BooleanField()),
        ).alias(_recorded=F('_success') + F('_fail') + F('_warning'),
                _success_fail=F('_success') + F('_fail'))
        missing = Q(_blocked=False, _size__gt=F('_recorded'))
        known_statuses = [item.value for item in TaskEnum]
        flags = {
            '_active': missing & Q(status__in=(TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value)),
            '_failure': (Q(_blocked=True, _fail__gt=0)
                         | Q(_blocked=False, _fail__gt=0, _success__lt=F('_size'))
                         | (missing & (Q(status=TaskEnum.FAIL.value) | ~Q(status__in=known_statuses)))),
            '_infrastructure': Q(_blocked=True, _fail__lt=F('_size')),
            '_warn': (Q(_blocked=False, _warning__gt=0, _success_fail__lt=F('_size'))
                      | (missing & Q(status=TaskEnum.WARNING.value))),
            '_stopped': missing & Q(status=TaskEnum.STOPPED.value),
            '_passed': Q(_blocked=False, _success__gt=0) | (missing & Q(status=TaskEnum.SUCCESS.value)),
        }

        def any_row(condition):
            return Max(Case(When(condition, then=Value(1)), default=Value(0), output_field=IntegerField()))

        grouped = details.values('test_suite_id').annotate(
            **{name: any_row(Q(is_excluded=False) & condition) for name, condition in flags.items()},
            _excluded=any_row(Q(is_excluded=True)),
            _included=any_row(Q(is_excluded=False)),
        ).annotate(_conclusion=Case(
            When(_active=1, then=Value(TaskEnum.PROCEED.value)),
            When(_excluded=1, _included=0, then=Value(TaskEnum.SUCCESS.value)),
            When(_raw_status=TaskEnum.STOPPED.value, then=Value(TaskEnum.STOPPED.value)),
            When(_raw_status=TaskEnum.FAIL.value, _excluded=0, _infrastructure=0,
                 then=Value(TaskEnum.FAIL.value)),
            When(_failure=1, then=Value(TaskEnum.FAIL.value)),
            When(_infrastructure=1, then=Value(TaskEnum.INFRASTRUCTURE_BLOCKED.value)),
            When(_warn=1, then=Value(TaskEnum.WARNING.value)),
            When(_stopped=1, then=Value(TaskEnum.STOPPED.value)),
            When(_passed=1, then=Value(TaskEnum.SUCCESS.value)),
            default=F('_raw_status'), output_field=IntegerField(),
        )).values('_conclusion')[:1]
        return queryset.alias(_report_filter_conclusion=Case(
            When(Q(retained_summary__isnull=False) & ~Q(retained_summary={}), then=F('status')),
            When(status__in=(TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value), then=F('status')),
            default=Coalesce(Subquery(grouped, output_field=IntegerField()), F('status')),
            output_field=IntegerField(),
        ))

    @classmethod
    def filter_status(cls, queryset, values):
        if not values or any(not str(value).isdigit() for value in values):
            return queryset.none()
        return cls.with_conclusion(queryset).filter(_report_filter_conclusion__in=[int(value) for value in values])
