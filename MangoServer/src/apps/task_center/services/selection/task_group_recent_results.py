from collections import defaultdict

from mangotools.enums import TaskEnum

from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.task_center.services.selection.recent_results import TaskRecentResultService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService


class TaskGroupRecentResultService:
    """批量汇总每个任务组最近七次执行，统计原报告重试后的当前结果。"""

    @classmethod
    def get_recent_results(cls, group_ids: list[int]) -> dict:
        result = {str(group_id): [] for group_id in group_ids}
        if not group_ids:
            return result
        executions = list(ScheduleFireQuerySelector.recent_executions_for_groups(group_ids))
        fires = list(ScheduleFire.objects.filter(group_execution_id__in=[item.id for item in executions])
                     .select_related('test_suite'))
        by_execution = defaultdict(list)
        by_suite = defaultdict(list)
        for fire in fires:
            by_execution[fire.group_execution_id].append(fire)
        for row in TestSuiteDetails.objects.filter(
                test_suite_id__in=[fire.test_suite_id for fire in fires if fire.test_suite_id],
        ).values('test_suite_id', 'status', 'case_sum', 'success', 'fail', 'warning', 'is_excluded', 'summary_data'):
            by_suite[row['test_suite_id']].append(row)
        for execution in executions:
            result[str(execution.task_group_id)].append(cls.summarize(
                execution, by_execution[execution.id], by_suite,
            ))
        return result

    @staticmethod
    def summarize(execution, fires, by_suite) -> dict:
        suites = [fire.test_suite for fire in fires if fire.test_suite_id]
        rows = [row for suite in suites for row in by_suite.get(suite.id, [])]
        counts = TestSuiteSummaryService.effective_summary_from_rows(rows)
        for suite in suites:
            snapshot = getattr(suite, 'retained_summary', None)
            if snapshot:
                for key, value in snapshot['execution_summary'].items():
                    counts[key] = counts.get(key, 0) + value
        total = counts['total']
        finished_at = execution.finished_at
        pending = (not finished_at and len(fires) < execution.expected_count) or any(
            not fire.test_suite_id and fire.status in (
                ScheduleFireStatusEnum.PENDING.value, ScheduleFireStatusEnum.DISPATCHING.value,
            ) for fire in fires
        )
        active = pending or counts['proceed'] or counts['stay_begin'] or any(
            suite.status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value) for suite in suites
        )
        if active:
            status = TaskEnum.PROCEED.value
        elif not suites:
            status = TaskEnum.FAIL.value
        elif any(suite.status == TaskEnum.FAIL.value and not by_suite.get(suite.id) for suite in suites):
            status = TaskEnum.FAIL.value
        else:
            seed = TaskEnum.STOPPED.value if any(
                s.status == TaskEnum.STOPPED.value for s in suites) else TaskEnum.SUCCESS.value
            status = TaskRecentResultService._result_status(seed, counts, total)
        started = min((suite.create_time for suite in suites), default=execution.planned_at)
        updated = max((suite.update_time for suite in suites), default=finished_at or execution.update_time)
        return {
            'group_execution_id': execution.id,
            'test_env': execution.test_env,
            'test_env_text': EnvironmentEnum.get_value(execution.test_env),
            'status': status,
            'status_key': TaskRecentResultService.STATUS_KEYS.get(status, 'fail'),
            'status_text': TaskEnum.get_value(status) if suites or active else '生成失败',
            'create_time': TaskRecentResultService._format_time(started),
            'update_time': TaskRecentResultService._format_time(updated),
            'duration_ms': max(int((updated - started).total_seconds() * 1000), 0),
            'total': total, **counts,
            'pass_rate': None if total and counts.get('blocked') == total else round(counts['success'] / total * 100, 2) if total else (100 if counts['excluded_count'] else None),
        }
