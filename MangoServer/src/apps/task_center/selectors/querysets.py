from src.apps.task_center.constants import RECENT_EXECUTION_LIMIT
from src.apps.task_center.models import ExecutorTask, Tasks, TasksDetails, TimeTasks


class TaskCenterQuerySelector:
    @staticmethod
    def tasks():
        return Tasks.objects.all()

    @staticmethod
    def tasks_details():
        return TasksDetails.objects.all()

    @staticmethod
    def time_tasks():
        return TimeTasks.objects.all()

    @staticmethod
    def executor_tasks():
        return ExecutorTask.objects.all()


from src.apps.task_center.models import (
    ScheduleFire,
    ScheduledTaskGroupExecution,
)


class ScheduleFireQuerySelector:
    @staticmethod
    def recent_executions_for_groups(group_ids: list[int], limit: int = RECENT_EXECUTION_LIMIT):
        from django.db.models import F, Window
        from django.db.models.functions import RowNumber

        return ScheduledTaskGroupExecution.objects.filter(
            task_group_id__in=group_ids,
        ).annotate(recent_rank=Window(
            expression=RowNumber(), partition_by=[F('task_group_id')],
            order_by=[F('planned_at').desc(), F('id').desc()],
        )).filter(recent_rank__lte=limit).order_by('task_group_id', '-planned_at', '-id')

    @staticmethod
    def latest_group_executions(group_id: int) -> list[dict]:
        from django.db.models import OuterRef, Subquery

        latest = ScheduledTaskGroupExecution.objects.filter(
            task_group_id=group_id, test_env=OuterRef('test_env'),
        ).order_by('-planned_at', '-id').values('id')[:1]
        return list(ScheduledTaskGroupExecution.objects.filter(
            task_group_id=group_id, id=Subquery(latest),
        ).order_by('test_env').values('id', 'test_env', 'planned_at', 'task_group_name', 'notice_group__name'))

    @staticmethod
    def schedule_fire():
        return ScheduleFire.objects.all()

    @staticmethod
    def scheduled_task_group_execution():
        return ScheduledTaskGroupExecution.objects.all()
