from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.selectors.execution_efficiency_metrics import timing_snapshot
from src.apps.test_center.selectors.report_progress import ReportProgressSelector
from src.apps.test_center.services.reporting.test_suite.effectiveness import AutomationEffectivenessService as Effectiveness
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary


class PlatformBlockedStatisticsTests(SimpleTestCase):
    @staticmethod
    def row(**extra):
        return {'id': 1, 'case_id': 1, 'type': TestCaseTypeEnum.API.value, 'case_sum': 2,
                'status': TaskEnum.INFRASTRUCTURE_BLOCKED.value, 'success': 0, 'fail': 0, 'warning': 0, **extra}

    @staticmethod
    def details(rows):
        query = MagicMock()
        query.values.return_value = rows
        return query

    def test_empty_status_distribution_covers_every_enum(self):
        result = Effectiveness._status_distribution(self.details([]))
        self.assertEqual({item['status'] for item in result}, {item.value for item in TaskEnum})
        self.assertTrue(all(item['value'] == 0 for item in result))

    def test_all_statuses_have_distinct_buckets_including_blocked(self):
        rows = [self.row(status=status.value) for status in TaskEnum]
        result = Effectiveness._status_distribution(self.details(rows))
        self.assertEqual({item['status']: item['value'] for item in result}, {item.value: 2 for item in TaskEnum})

    def test_blocked_is_terminal_without_becoming_success_or_business_failure(self):
        counts = Summary.execution_status_counts_from_rows([self.row()])
        self.assertEqual(Summary.completed_execution_count(counts), 2)
        self.assertEqual((counts['success'], counts['fail'], counts['blocked']), (0, 0, 2))
        mixed = Summary.execution_status_counts_from_rows([self.row(fail=1)])
        self.assertEqual((mixed['fail'], mixed['blocked']), (1, 1))
        self.assertEqual(Summary.completed_execution_count(mixed), 2)
        counter = Summary.counter_data_from_rows([self.row()])
        self.assertEqual((counter['api_in_progress_case_sum'], counter['api_blocked']), (2, 2))

    def test_overview_and_period_cards_do_not_lose_blocked_counts(self):
        executions = MagicMock()
        executions.filter.return_value.values_list.return_value.distinct.return_value = []
        suites = MagicMock()
        suites.count.return_value = 1
        with patch.object(Effectiveness, '_first_feedback_metrics', return_value={
            'p95_seconds': None, 'sample_count': 0, 'report_count': 0, 'sample_coverage': 0,
        }):
            cards = Effectiveness._summary_cards(suites, self.details([self.row()]), executions)
        self.assertEqual(cards['completion_rate'], 100.0)
        self.assertEqual(cards['final_pass_rate'], 0.0)
        self.assertEqual((cards['blocked_count'], cards['failed_count'], cards['unfinished_count']), (2, 0, 0))
        now = timezone.now()
        period = Effectiveness._period_quality_item('example', 'Example', now, now + timedelta(days=1), cards)
        self.assertEqual(period['blocked_count'], 2)
        self.assertIn(TaskEnum.INFRASTRUCTURE_BLOCKED.value, Effectiveness.COMPLETED_STATUSES)

    def test_environment_scene_scope_and_daily_rates_include_blocked_terminal_results(self):
        env = next(iter(EnvironmentEnum)).value
        from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum
        scene = next(iter(AutomationExecutionSceneEnum)).value
        now = timezone.now()
        row = self.row(test_suite__test_env=env, test_suite__execution_scenes=[scene],
                       test_suite__execution_scope=0, test_suite__create_time=now)
        suites, executions = MagicMock(), MagicMock()
        suites.values.return_value.annotate.return_value = [{'test_env': env, 'count': 1}]
        executions.values.return_value.annotate.return_value = []
        with patch.object(EnvironmentEnum, 'get_value', return_value='Example'):
            environments = Effectiveness._environment_quality(suites, self.details([row]), executions)
        self.assertEqual(environments[0]['completion_rate'], 100.0)
        self.assertEqual(environments[0]['final_pass_rate'], 0.0)
        for method in (Effectiveness._scene_distribution, Effectiveness._scope_distribution):
            self.assertEqual(method(self.details([row]))[0]['final_pass_rate'], 0.0)
        self.assertEqual(Effectiveness._trend(self.details([row]), now, now + timedelta(seconds=1))[0]['final_pass_rate'], 0.0)

    def test_efficiency_does_not_keep_growing_duration_for_blocked_report(self):
        now = timezone.now()
        report = {'id': 1, 'name': 'Example', 'project_product': 'Example', 'module': 'Example', 'create_time': now}
        detail = self.row(test_suite_id=1)
        trace = {'id': 1, 'trace_id': 'example-trace', 'test_suite_id': 1, 'test_suite_detail_id': 1,
                 'case_id': 1, 'case_name': 'Example',
                 'status': TaskEnum.INFRASTRUCTURE_BLOCKED.value, 'started_at': now,
                 'finished_at': now + timedelta(seconds=2), 'duration_ms': 2000}
        result = timing_snapshot([report], [detail], [trace], [],
                                 SimpleNamespace(start_at=now, end_at=now + timedelta(days=1)))
        self.assertEqual(result['summary']['completed'], 1)
        self.assertEqual(result['basic'][1]['completed'], 1)
        self.assertEqual(result['trend'][0]['completed'], 1)
        self.assertFalse(result['slow_reports'][0]['running'])
        self.assertEqual(result['slow_reports'][0]['observed_span_ms'], 2000)

    def test_module_matrix_and_automation_type_rates_include_blocked(self):
        from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum
        now = timezone.now()
        scene = next(iter(AutomationExecutionSceneEnum)).value
        env = next(iter(EnvironmentEnum)).value
        row = self.row(test_suite_id=1, test_suite__tasks_id=1, test_suite__create_time=now,
                       test_suite__module_id=None, test_suite__project_product_id=1,
                       test_suite__project_product__name='Example',
                       test_suite__project_product__project__name='Example',
                       test_suite__test_env=env, test_suite__execution_scenes=[scene])
        with patch('src.apps.test_center.services.reporting.test_suite.effectiveness_parts.module.ProductModuleService.with_full_paths',
                   return_value=[]):
            modules = Effectiveness._aggregate_module_quality(self.details([row]))
        self.assertEqual(modules[0]['final_pass_rate'], 0.0)
        self.assertEqual(modules[0]['failed_count'], 0)
        with patch.object(EnvironmentEnum, 'get_value', return_value='Example'):
            matrix = Effectiveness._scene_matrix(MagicMock(), self.details([row]))
        self.assertEqual(matrix['values'][str(env)][scene]['final_pass_rate'], 0.0)
        executions = MagicMock()
        executions.filter.return_value.values_list.return_value.distinct.return_value = []
        types = Effectiveness._automation_type_quality(self.details([row]), executions)
        self.assertEqual(types[0]['final_pass_rate'], 0.0)
        self.assertEqual(types[0]['unfinished_count'], 0)

    @patch('src.apps.test_center.selectors.report_progress.TestSuiteDetails.objects')
    def test_progress_terminal_count_includes_blocked(self, objects):
        ReportProgressSelector.snapshots([1])
        annotation = objects.filter.return_value.order_by.return_value.values.return_value.annotate
        terminal_filter = annotation.call_args.kwargs['terminal_count'].filter
        self.assertIn(TaskEnum.INFRASTRUCTURE_BLOCKED.value, dict(terminal_filter.children)['status__in'])
