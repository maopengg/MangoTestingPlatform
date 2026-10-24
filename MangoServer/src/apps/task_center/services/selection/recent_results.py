from collections import defaultdict

from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.constants import RECENT_EXECUTION_LIMIT
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService


class TaskRecentResultService:
    """批量返回定时任务最近执行质量，避免列表页逐任务查询。"""

    DEFAULT_LIMIT = RECENT_EXECUTION_LIMIT
    MAX_LIMIT = RECENT_EXECUTION_LIMIT

    STATUS_KEYS = {
        TaskEnum.FAIL.value: 'fail',
        TaskEnum.SUCCESS.value: 'success',
        TaskEnum.STAY_BEGIN.value: 'stay_begin',
        TaskEnum.PROCEED.value: 'proceed',
        TaskEnum.WARNING.value: 'warning',
        TaskEnum.STOPPED.value: 'stopped',
    }

    @classmethod
    def normalize_limit(cls, value) -> int:
        try:
            limit = int(value or cls.DEFAULT_LIMIT)
        except (TypeError, ValueError):
            limit = cls.DEFAULT_LIMIT
        return min(max(limit, 1), cls.MAX_LIMIT)

    @classmethod
    def get_recent_results(cls, task_ids: list[int], limit: int = DEFAULT_LIMIT) -> dict:
        if not task_ids:
            return {}

        limit = cls.normalize_limit(limit)
        suites = []
        task_result_counts = defaultdict(int)
        suite_queryset = (
            TestSuite.objects.filter(tasks_id__in=task_ids)
            .values(
                'id',
                'tasks_id',
                'test_env',
                'status',
                'create_time',
                'update_time',
                'retained_summary',
            )
            .order_by('tasks_id', '-create_time', '-id')
        )
        for suite in suite_queryset.iterator(chunk_size=200):
            task_id = suite['tasks_id']
            if task_result_counts[task_id] >= limit:
                continue
            suites.append(suite)
            task_result_counts[task_id] += 1
        if not suites:
            return {str(task_id): [] for task_id in task_ids}

        detail_rows = TestSuiteDetails.objects.filter(
            test_suite_id__in=[item['id'] for item in suites]
        ).values(
            'test_suite_id',
            'status',
            'case_sum',
            'success',
            'fail',
            'warning',
            'is_excluded',
        )
        details_by_suite = defaultdict(list)
        for row in detail_rows:
            details_by_suite[row['test_suite_id']].append(row)

        result = {str(task_id): [] for task_id in task_ids}
        for suite in suites:
            counts = TestSuiteSummaryService.effective_summary_from_rows(
                details_by_suite.get(suite['id'], [])
            )
            if suite.get('retained_summary'):
                counts = suite['retained_summary']['execution_summary']
            total = counts['total']
            status = cls._result_status(suite['status'], counts, total)
            create_time = suite['create_time']
            update_time = suite['update_time']
            duration_ms = 0
            if create_time and update_time:
                duration_ms = max(int((update_time - create_time).total_seconds() * 1000), 0)
            result[str(suite['tasks_id'])].append({
                'test_suite_id': None if suite.get('retained_summary') else suite['id'],
                'report_retained': not bool(suite.get('retained_summary')),
                'status': status,
                'status_key': cls.STATUS_KEYS.get(status, 'fail'),
                'status_text': TaskEnum.obj().get(status, '失败'),
                'excluded_count': counts['excluded_count'],
                'test_env': suite['test_env'],
                'test_env_text': EnvironmentEnum.obj().get(suite['test_env'], '-'),
                'create_time': cls._format_time(create_time),
                'update_time': cls._format_time(update_time),
                'duration_ms': duration_ms,
                'total': total,
                'success': counts['success'],
                'fail': counts['fail'],
                'warning': counts['warning'],
                'proceed': counts['proceed'],
                'stay_begin': counts['stay_begin'],
                'stopped': counts['stopped'],
                'pass_rate': round(counts['success'] / total * 100, 2) if total else (100 if counts['excluded_count'] else None),
            })
        return result

    @classmethod
    def _result_status(cls, suite_status: int, counts: dict, total: int) -> int:
        if counts.get('excluded_count') and suite_status not in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
            return TestSuiteSummaryService.conclusion_status(suite_status, counts, total)
        if suite_status in {
            TaskEnum.STAY_BEGIN.value,
            TaskEnum.PROCEED.value,
            TaskEnum.STOPPED.value,
        }:
            return suite_status
        if counts['fail'] > 0:
            return TaskEnum.FAIL.value
        if counts['warning'] > 0:
            return TaskEnum.WARNING.value
        if counts['success'] > 0:
            return TaskEnum.SUCCESS.value
        if suite_status in cls.STATUS_KEYS:
            return suite_status
        return TaskEnum.STAY_BEGIN.value

    @staticmethod
    def _format_time(value) -> str | None:
        if value is None:
            return None
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')
