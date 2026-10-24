from datetime import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from src.apps.task_center.services.scheduling.upcoming_tasks import UpcomingTaskService


class FakeTaskQuerySet(list):
    def filter(self, **kwargs):
        status = kwargs.get('status')
        return FakeTaskQuerySet(item for item in self if item.status == status)


class UpcomingTaskServiceTests(SimpleTestCase):
    @staticmethod
    def task(task_id: int, cron: str, status: int = 1):
        timing_strategies = [SimpleNamespace(id=20, name='测试策略', cron=cron)]
        return SimpleNamespace(
            id=task_id,
            name=f'任务{task_id}',
            status=status,
            test_envs=[0],
            execution_scenes=['stability_monitoring'],
            execution_scope='full_product',
            project_product_id=10,
            project_product=SimpleNamespace(
                name='测试产品',
                project_id=9,
                project=SimpleNamespace(name='测试项目'),
            ),
            timing_strategies=SimpleNamespace(all=lambda: timing_strategies),
            case_people_id=30,
            case_people=SimpleNamespace(name='测试人员'),
        )

    def test_upcoming_only_returns_enabled_tasks_sorted_by_next_run(self):
        now = datetime(2026, 8, 20, 10, 3, 0)
        queryset = FakeTaskQuerySet([
            self.task(3, '0 11 * * *'),
            self.task(2, '*/5 * * * *'),
            self.task(1, '*/5 * * * *'),
            self.task(4, '*/1 * * * *', status=0),
        ])

        result = UpcomingTaskService.upcoming(queryset, now=now)

        self.assertEqual([item.task.id for item in result], [1, 2, 3])
        self.assertEqual(result[0].next_run_at.hour, 10)
        self.assertEqual(result[0].next_run_at.minute, 5)
        self.assertEqual(result[2].next_run_at.hour, 11)

    def test_invalid_cron_is_not_returned(self):
        queryset = FakeTaskQuerySet([
            self.task(1, 'invalid cron'),
            self.task(2, '0 11 * * *'),
        ])

        result = UpcomingTaskService.upcoming(
            queryset,
            now=datetime(2026, 8, 20, 10, 3, 0),
        )

        self.assertEqual([item.task.id for item in result], [2])

    def test_multiple_strategies_use_the_earliest_next_run(self):
        task = self.task(1, '0 12 * * *')
        strategies = [
            SimpleNamespace(id=20, name='中午策略', cron='0 12 * * *'),
            SimpleNamespace(id=21, name='五分钟策略', cron='*/5 * * * *'),
        ]
        task.timing_strategies = SimpleNamespace(all=lambda: strategies)

        result = UpcomingTaskService.upcoming(
            FakeTaskQuerySet([task]),
            now=datetime(2026, 8, 20, 10, 3, 0),
        )

        self.assertEqual(result[0].next_run_at.hour, 10)
        self.assertEqual(result[0].next_run_at.minute, 5)

    def test_paginate_returns_each_page_and_total(self):
        queryset = FakeTaskQuerySet([
            self.task(task_id, '*/5 * * * *')
            for task_id in range(1, 46)
        ])

        first_page, total = UpcomingTaskService.paginate(
            queryset,
            page=1,
            page_size=20,
            now=datetime(2026, 8, 20, 10, 3, 0),
        )
        third_page, _ = UpcomingTaskService.paginate(
            queryset,
            page=3,
            page_size=20,
            now=datetime(2026, 8, 20, 10, 3, 0),
        )

        self.assertEqual(total, 45)
        self.assertEqual(len(first_page), 20)
        self.assertEqual([item.task.id for item in third_page], [41, 42, 43, 44, 45])

    def test_serialized_time_supports_naive_django_time(self):
        item = UpcomingTaskService.upcoming(
            FakeTaskQuerySet([self.task(1, '*/5 * * * *')]),
            now=datetime(2026, 8, 20, 10, 3, 0),
        )[0]

        result = UpcomingTaskService.serialize(
            item,
            now=datetime(2026, 8, 20, 10, 3, 0),
        )

        self.assertEqual(result['next_run_time'], '2026-08-20 10:05:00')
        self.assertEqual(result['seconds_until_run'], 120)
        self.assertIsNone(result['latest_result_status'])
        self.assertIn('+08:00', result['next_run_at'])
        self.assertEqual(result['project_product'], {
            'id': 10,
            'name': '测试产品',
            'project': {'id': 9, 'name': '测试项目'},
        })
        self.assertEqual(result['test_envs'], [0])
        self.assertEqual(result['timing_strategies'][0]['name'], '测试策略')

    def test_serialize_includes_latest_execution_result_status(self):
        task = self.task(1, '*/5 * * * *')
        task.latest_result_status = 0
        item = UpcomingTaskService.upcoming(
            FakeTaskQuerySet([task]),
            now=datetime(2026, 8, 20, 10, 3, 0),
        )[0]

        result = UpcomingTaskService.serialize(
            item,
            now=datetime(2026, 8, 20, 10, 3, 0),
        )

        self.assertEqual(result['latest_result_status'], 0)
