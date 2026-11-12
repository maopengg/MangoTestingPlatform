from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails


class ReportProgressSelector:
    @staticmethod
    def running_owners(*, report_ids=None, attempts=None):
        """当前执行持有者及不可变领取时间；续租会修改 push_time，不能用它划分 Trace 代次。"""
        rows = TestSuiteDetails.objects.filter(type=TestCaseTypeEnum.API.value, status=TaskEnum.PROCEED.value)
        if report_ids is not None:
            rows = rows.filter(test_suite_id__in=report_ids)
        elif attempts:
            condition = Q()
            for detail_id, attempt in attempts.items():
                condition |= Q(id=detail_id, retry=attempt)
            rows = rows.filter(condition)
        else:
            return []
        result = []
        for row in rows.order_by('id').values('id', 'retry', 'push_time', 'test_suite_id',
                                            'summary_data__meta__dispatch_started_at'):
            stamp = row['summary_data__meta__dispatch_started_at']
            try:
                started = parse_datetime(stamp) if isinstance(stamp, str) else None
            except ValueError:
                started = None
            result.append({'detail_id': row['id'], 'attempt': row['retry'],
                           'started_at': started or row['push_time'], 'report_id': row['test_suite_id']})
        return result

    @staticmethod
    def active_ids(after_id=0, limit=100):
        return list(TestSuite.objects.filter(status=TaskEnum.PROCEED.value, id__gt=after_id)
                    .order_by('id').values_list('id', flat=True)[:limit])

    @staticmethod
    def snapshots(report_ids):
        terminal = [TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value]
        return list(TestSuiteDetails.objects.filter(test_suite_id__in=report_ids,
            type=TestCaseTypeEnum.API.value).order_by().values('test_suite_id').annotate(
                terminal_count=Count('id', filter=Q(status__in=terminal)),
                running_count=Count('id', filter=Q(status=TaskEnum.PROCEED.value)),
                pending_count=Count('id', filter=Q(status=TaskEnum.STAY_BEGIN.value))))
