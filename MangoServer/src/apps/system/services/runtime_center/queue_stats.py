from django.db.models import Count
from mangotools.enums import TaskEnum

from src.apps.system.enums import ExecutorTaskStatusEnum
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.models import ExecutorTask
from src.apps.task_center.models import ScheduleFire
from src.apps.test_center.models import TestSuiteDetails


class QueueStatsService:
    CASE_TYPE_UI = 0
    CASE_TYPE_API = 1
    CASE_TYPE_PYTEST = 2

    @classmethod
    def get_stats(cls) -> dict:
        detail_counts = cls.test_suite_detail_counts()
        fire_counts = cls.schedule_fire_counts()
        executor_task_counts = cls.executor_task_counts()
        return {
            'api': cls.build_case_queue(detail_counts, cls.CASE_TYPE_API),
            'ui': cls.build_case_queue(detail_counts, cls.CASE_TYPE_UI),
            'pytest': cls.build_case_queue(detail_counts, cls.CASE_TYPE_PYTEST),
            'schedule_fire': {
                'pending': fire_counts.get(ScheduleFireStatusEnum.PENDING.value, 0),
                'running': fire_counts.get(ScheduleFireStatusEnum.DISPATCHING.value, 0),
            },
            'executor_task': {
                'pending': (
                        executor_task_counts.get(ExecutorTaskStatusEnum.WAITING_EXECUTOR.value, 0)
                        + executor_task_counts.get(ExecutorTaskStatusEnum.PENDING.value, 0)
                        + executor_task_counts.get(ExecutorTaskStatusEnum.CLAIMED.value, 0)
                ),
                'running': executor_task_counts.get(ExecutorTaskStatusEnum.RUNNING.value, 0),
                'success': executor_task_counts.get(ExecutorTaskStatusEnum.SUCCESS.value, 0),
                'failed': executor_task_counts.get(ExecutorTaskStatusEnum.FAILED.value, 0),
                'timeout': executor_task_counts.get(ExecutorTaskStatusEnum.TIMEOUT.value, 0),
                'interrupted': executor_task_counts.get(ExecutorTaskStatusEnum.INTERRUPTED.value, 0),
            },
        }

    @classmethod
    async def aget_stats(cls) -> dict:
        detail_counts = await cls.atest_suite_detail_counts()
        fire_counts = await cls.aschedule_fire_counts()
        executor_task_counts = await cls.aexecutor_task_counts()
        return {
            'api': cls.build_case_queue(detail_counts, cls.CASE_TYPE_API),
            'ui': cls.build_case_queue(detail_counts, cls.CASE_TYPE_UI),
            'pytest': cls.build_case_queue(detail_counts, cls.CASE_TYPE_PYTEST),
            'schedule_fire': {
                'pending': fire_counts.get(ScheduleFireStatusEnum.PENDING.value, 0),
                'running': fire_counts.get(ScheduleFireStatusEnum.DISPATCHING.value, 0),
            },
            'executor_task': {
                'pending': (
                        executor_task_counts.get(ExecutorTaskStatusEnum.WAITING_EXECUTOR.value, 0)
                        + executor_task_counts.get(ExecutorTaskStatusEnum.PENDING.value, 0)
                        + executor_task_counts.get(ExecutorTaskStatusEnum.CLAIMED.value, 0)
                ),
                'running': executor_task_counts.get(ExecutorTaskStatusEnum.RUNNING.value, 0),
                'success': executor_task_counts.get(ExecutorTaskStatusEnum.SUCCESS.value, 0),
                'failed': executor_task_counts.get(ExecutorTaskStatusEnum.FAILED.value, 0),
                'timeout': executor_task_counts.get(ExecutorTaskStatusEnum.TIMEOUT.value, 0),
                'interrupted': executor_task_counts.get(ExecutorTaskStatusEnum.INTERRUPTED.value, 0),
            },
        }

    @staticmethod
    def test_suite_detail_counts() -> dict[tuple[int, int], int]:
        rows = TestSuiteDetails.objects.values('type', 'status').annotate(count=Count('id'))
        return {(item['type'], item['status']): item['count'] for item in rows}

    @staticmethod
    async def atest_suite_detail_counts() -> dict[tuple[int, int], int]:
        rows = TestSuiteDetails.objects.values('type', 'status').annotate(count=Count('id'))
        return {(item['type'], item['status']): item['count'] async for item in rows}

    @staticmethod
    def schedule_fire_counts() -> dict[int, int]:
        rows = ScheduleFire.objects.values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] for item in rows}

    @staticmethod
    async def aschedule_fire_counts() -> dict[int, int]:
        rows = ScheduleFire.objects.values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] async for item in rows}

    @staticmethod
    def executor_task_counts() -> dict[str, int]:
        rows = ExecutorTask.objects.values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] for item in rows}

    @staticmethod
    async def aexecutor_task_counts() -> dict[str, int]:
        rows = ExecutorTask.objects.values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] async for item in rows}

    @classmethod
    def build_case_queue(cls, counts: dict[tuple[int, int], int], case_type: int) -> dict:
        return {
            'pending': counts.get((case_type, TaskEnum.STAY_BEGIN.value), 0),
            'running': counts.get((case_type, TaskEnum.PROCEED.value), 0),
        }

    @classmethod
    def pending_total(cls, queues: dict) -> int:
        return sum(item.get('pending', 0) for item in queues.values())
