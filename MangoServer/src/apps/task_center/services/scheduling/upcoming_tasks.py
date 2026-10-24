from dataclasses import dataclass
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService


@dataclass(frozen=True)
class UpcomingTask:
    task: object
    next_run_at: datetime


class UpcomingTaskService:
    """计算已启用定时任务的下一次触发时间。"""

    DEFAULT_LIMIT = 20

    @staticmethod
    def aware_now(now: datetime | None = None) -> datetime:
        current = now or timezone.now()
        current_timezone = timezone.get_current_timezone()
        if timezone.is_naive(current):
            return timezone.make_aware(current, current_timezone)
        return timezone.localtime(current, current_timezone)

    @classmethod
    def next_run_at(cls, cron: str, now: datetime | None = None) -> datetime | None:
        try:
            current_timezone = timezone.get_current_timezone()
            trigger = CronTrigger.from_crontab(cron, timezone=current_timezone)
            return trigger.get_next_fire_time(None, cls.aware_now(now))
        except (TypeError, ValueError):
            return None

    @classmethod
    def upcoming(
            cls,
            queryset,
            limit: int | None = DEFAULT_LIMIT,
            offset: int = 0,
            now: datetime | None = None,
    ):
        current = cls.aware_now(now)
        next_run_by_cron: dict[str, datetime | None] = {}
        result: list[UpcomingTask] = []

        for task in queryset.filter(status=StatusEnum.SUCCESS.value):
            next_runs = []
            for timing_strategy in task.timing_strategies.all():
                cron = timing_strategy.cron
                if cron not in next_run_by_cron:
                    next_run_by_cron[cron] = cls.next_run_at(cron, current)
                if next_run_by_cron[cron] is not None:
                    next_runs.append(next_run_by_cron[cron])
            next_run_at = min(next_runs) if next_runs else None
            if next_run_at is not None:
                result.append(UpcomingTask(task=task, next_run_at=next_run_at))

        result.sort(key=lambda item: (item.next_run_at, item.task.id))
        start = max(0, offset)
        if limit is None:
            return result[start:]
        return result[start:start + max(0, limit)]

    @classmethod
    def paginate(cls, queryset, page: int, page_size: int, now: datetime | None = None):
        result = cls.upcoming(queryset, limit=None, now=now)
        start = max(0, page - 1) * page_size
        return result[start:start + page_size], len(result)

    @classmethod
    def serialize(cls, item: UpcomingTask, now: datetime | None = None) -> dict:
        current = cls.aware_now(now)
        next_run_at = timezone.localtime(item.next_run_at, timezone.get_current_timezone())
        task = item.task
        return {
            'id': task.id,
            'name': task.name,
            'test_envs': task.test_envs,
            'execution_scenes': ScheduledTaskCaseSelectionService.task_execution_scenes(task),
            'execution_scope': task.execution_scope,
            'project_product': {
                'id': task.project_product_id,
                'name': task.project_product.name,
                'project': {
                    'id': task.project_product.project_id,
                    'name': task.project_product.project.name,
                },
            },
            'timing_strategies': [
                {
                    'id': timing_strategy.id,
                    'name': timing_strategy.name,
                    'cron': timing_strategy.cron,
                }
                for timing_strategy in task.timing_strategies.all()
            ],
            'case_people': {
                'id': task.case_people_id,
                'name': task.case_people.name,
            },
            'next_run_at': next_run_at.isoformat(),
            'next_run_time': next_run_at.strftime('%Y-%m-%d %H:%M:%S'),
            'seconds_until_run': max(0, int((next_run_at - current).total_seconds())),
            'latest_result_status': getattr(task, 'latest_result_status', None),
        }
