from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.models import Tasks, TimeTasks
from src.apps.test_center.models import Project, ProjectProduct, TestSuite
from src.apps.test_center.services.test_suite.report_overview import TestSuiteReportOverviewService
from src.apps.user.models import User


class TestSuiteReportOverviewServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        project = Project.objects.create(name='报告概览项目')
        self.product = ProjectProduct.objects.create(project=project, name='报告概览产品')
        self.other_product = ProjectProduct.objects.create(project=project, name='其他产品')
        self.user = User.objects.create(
            name='报告概览用户',
            username='report_overview_user',
            password='pwd',
            is_super_admin=True,
        )
        strategy = TimeTasks.objects.create(name='报告概览策略', cron='0 0 * * *')
        self.task = Tasks.objects.create(
            project_product=self.product,
            name='每日回归',
            case_people=self.user,
            test_envs=[0],
        )
        self.task.timing_strategies.add(strategy)

    @staticmethod
    def request(**params):
        return SimpleNamespace(query_params=params, user=None, headers={})

    def create_suite(self, suite_id, status, *, task=None, product=None, weeks_ago=0):
        suite = TestSuite.objects.create(
            id=suite_id,
            project_product=product or self.product,
            test_env=0,
            user=self.user,
            tasks=task,
            status=status,
            is_notice=0,
        )
        TestSuite.objects.filter(id=suite.id).update(
            create_time=timezone.now() - timedelta(weeks=weeks_ago)
        )
        return suite

    def test_overview_uses_report_status_and_source_counts(self):
        self.create_suite(51001, TaskEnum.SUCCESS.value)
        self.create_suite(51002, TaskEnum.FAIL.value, task=self.task)
        self.create_suite(51003, TaskEnum.WARNING.value, task=self.task, weeks_ago=1)

        result = TestSuiteReportOverviewService.overview(self.request())
        status_map = {item['status']: item['value'] for item in result['status_distribution']}

        self.assertEqual(result['total'], 3)
        self.assertEqual(status_map[TaskEnum.SUCCESS.value], 1)
        self.assertEqual(status_map[TaskEnum.FAIL.value], 1)
        self.assertEqual(status_map[TaskEnum.WARNING.value], 1)
        self.assertEqual(result['source_distribution'], {'batch': 1, 'scheduled': 2})
        self.assertEqual(len(result['trend']), 12)
        self.assertIn('-', result['trend'][-1]['label'])

    def test_overview_applies_project_product_filter(self):
        self.create_suite(52001, TaskEnum.SUCCESS.value)
        self.create_suite(
            52002,
            TaskEnum.FAIL.value,
            product=self.other_product,
        )

        result = TestSuiteReportOverviewService.overview(
            self.request(project_product=str(self.product.id))
        )

        self.assertEqual(result['total'], 1)
        self.assertEqual(result['successSun'], 1)
        self.assertEqual(result['failSun'], 0)

    def test_overview_applies_scheduled_report_source_filter(self):
        self.create_suite(52501, TaskEnum.SUCCESS.value)
        self.create_suite(52502, TaskEnum.FAIL.value, task=self.task)
        self.create_suite(52503, TaskEnum.WARNING.value, task=self.task)

        scheduled_result = TestSuiteReportOverviewService.overview(
            self.request(**{'tasks__isnull': 'false'})
        )
        non_scheduled_result = TestSuiteReportOverviewService.overview(
            self.request(**{'tasks__isnull': 'true'})
        )

        self.assertEqual(scheduled_result['total'], 2)
        self.assertEqual(
            scheduled_result['source_distribution'],
            {'batch': 0, 'scheduled': 2},
        )
        self.assertEqual(non_scheduled_result['total'], 1)
        self.assertEqual(
            non_scheduled_result['source_distribution'],
            {'batch': 1, 'scheduled': 0},
        )

    def test_overview_reuses_ten_minute_cache_for_same_filters(self):
        request = self.request(project_product=str(self.product.id), status='1')
        with (
            patch.object(
                TestSuiteReportOverviewService,
                '_build_overview',
                return_value={'total': 3, 'trend': []},
            ) as build_overview,
            patch.object(cache, 'set', wraps=cache.set) as cache_set,
        ):
            first = TestSuiteReportOverviewService.overview(request)
            second = TestSuiteReportOverviewService.overview(request)

        self.assertEqual(first, second)
        build_overview.assert_called_once_with(request)
        self.assertEqual(cache_set.call_args.args[2], 60 * 10)

    def test_overview_cache_isolated_by_filters_and_project_header(self):
        first_request = self.request(status='1')
        first_request.headers = {'X-Project-Product-Id': '1'}
        second_request = self.request(status='0')
        second_request.headers = {'X-Project-Product-Id': '2'}

        self.assertNotEqual(
            TestSuiteReportOverviewService._cache_key(first_request),
            TestSuiteReportOverviewService._cache_key(second_request),
        )
