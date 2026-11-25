from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.constants import RECENT_EXECUTION_LIMIT
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.task_center.services.selection.recent_results import TaskRecentResultService
from src.apps.task_center.services.selection.task_group_recent_results import TaskGroupRecentResultService


class TaskGroupRecentResultTests(SimpleTestCase):
    def test_pruned_success_uses_lightweight_counts(self):
        self.suite.retained_summary = {'execution_summary': {
            'total': 10, 'success': 10, 'fail': 0, 'warning': 0, 'proceed': 0,
            'stay_begin': 0, 'stopped': 0, 'excluded_count': 0, 'excluded_items': 0, 'raw_total': 10,
        }}
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, {})
        self.assertEqual(result['total'], 10)
        self.assertEqual(result['status_key'], 'success')
        self.assertEqual(result['pass_rate'], 100)

    def test_all_excluded_original_failure_shows_pass_and_100_percent(self):
        self.suite.status = TaskEnum.FAIL.value
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, {
            101: [{'status': TaskEnum.FAIL.value, 'case_sum': 10, 'success': 0, 'fail': 10,
                   'warning': 0, 'is_excluded': True}],
        })
        self.assertEqual(result['status_key'], 'success')
        self.assertEqual(result['pass_rate'], 100)
        self.assertEqual(result['excluded_count'], 10)

    def setUp(self):
        display_names = patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names', return_value={})
        display_names.start()
        self.addCleanup(display_names.stop)
        now = timezone.now()
        self.execution = SimpleNamespace(id=68, task_group_id=2, test_env=0,
                                         expected_count=2, planned_at=now, update_time=now,
                                         finished_at=None)
        self.suite = SimpleNamespace(id=101, status=TaskEnum.SUCCESS.value, create_time=now, update_time=now)
        self.fires = [SimpleNamespace(group_execution_id=68, test_suite_id=101, test_suite=self.suite,
                                      status=ScheduleFireStatusEnum.FAIL.value),
                      SimpleNamespace(group_execution_id=68, test_suite_id=None,
                                      status=ScheduleFireStatusEnum.SKIPPED.value)]

    def test_legacy_platform_block_is_counted_as_failed_execution(self):
        self.suite.status = TaskEnum.INFRASTRUCTURE_BLOCKED.value
        rows = {101: [{'status': 6, 'case_sum': 10, 'success': 0, 'fail': 0, 'warning': 0}]}
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, rows)
        self.assertEqual((result['status'], result['status_key'], result['blocked'], result['fail']), (0, 'fail', 0, 10))

    def test_current_results_replace_previous_failure_without_counting_generation_failure(self):
        rows = {101: [{'status': TaskEnum.SUCCESS.value, 'case_sum': 10, 'success': 10, 'fail': 0, 'warning': 0}]}
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, rows)
        self.assertEqual(result['status_key'], 'success')
        self.assertEqual(result['total'], 10)
        self.assertEqual(result['pass_rate'], 100)
        rows[101][0].update(success=8, fail=2)
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, rows)
        self.assertEqual(result['fail'], 2)
        self.assertEqual(result['status_key'], 'fail')
        self.assertEqual(result['pass_rate'], 80)

    def test_retrying_detail_makes_completed_batch_in_progress(self):
        self.execution.finished_at = self.execution.update_time
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, {
            101: [{'status': TaskEnum.STAY_BEGIN.value, 'case_sum': 10, 'success': 0, 'fail': 0, 'warning': 0}],
        })
        self.assertEqual(result['status_key'], 'proceed')
        self.assertEqual(result['stay_begin'], 10)

    def test_finalized_empty_batch_shows_generation_failure_with_fixed_duration(self):
        self.execution.expected_count = 25
        self.execution.status = TaskEnum.FAIL.value
        self.execution.finished_at = self.execution.planned_at + timedelta(seconds=10)
        self.execution.update_time = self.execution.planned_at + timedelta(hours=12)

        result = TaskGroupRecentResultService.summarize(self.execution, [], {})

        self.assertEqual(result['status_key'], 'fail')
        self.assertEqual(result['status_text'], '生成失败')
        self.assertEqual(result['duration_ms'], 10000)
        self.assertIsNone(result['pass_rate'])

    def test_unfinished_empty_batch_still_waits_for_generation(self):
        result = TaskGroupRecentResultService.summarize(self.execution, [], {})

        self.assertEqual(result['status_key'], 'proceed')

    def test_generation_pending_and_failed_are_distinguished(self):
        self.execution.expected_count = 1
        self.fires = [self.fires[1]]
        self.fires[0].status = ScheduleFireStatusEnum.PENDING.value
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, {})
        self.assertEqual(result['status_key'], 'proceed')
        self.fires[0].status = ScheduleFireStatusEnum.SKIPPED.value
        result = TaskGroupRecentResultService.summarize(self.execution, self.fires, {})
        self.assertEqual(result['status_text'], '生成失败')
        self.assertIsNone(result['pass_rate'])

    def test_bulk_lookup_preserves_recent_batches_and_groups_without_history(self):
        second = SimpleNamespace(**vars(self.execution))
        second.id = 67
        with (
            patch(
                'src.apps.task_center.services.selection.task_group_recent_results.ScheduleFireQuerySelector.recent_executions_for_groups',
                return_value=[self.execution, second]) as lookup,
            patch('src.apps.task_center.services.selection.task_group_recent_results.ScheduleFire.objects') as fires,
            patch(
                'src.apps.task_center.services.selection.task_group_recent_results.TestSuiteDetails.objects') as details,
        ):
            fires.filter.return_value.select_related.return_value = self.fires
            details.filter.return_value.values.return_value = []
            result = TaskGroupRecentResultService.get_recent_results([2, 3])
        lookup.assert_called_once_with([2, 3])
        fires.filter.assert_called_once()
        details.filter.assert_called_once()
        self.assertEqual([item['group_execution_id'] for item in result['2']], [68, 67])
        self.assertEqual(result['3'], [])

    def test_empty_page_does_not_query(self):
        with patch(
                'src.apps.task_center.services.selection.task_group_recent_results.ScheduleFireQuerySelector.recent_executions_for_groups') as lookup:
            self.assertEqual(TaskGroupRecentResultService.get_recent_results([]), {})
        lookup.assert_not_called()

    def test_selector_limits_each_group_to_recent_execution_limit_without_environment_partition(self):
        query = ScheduleFireQuerySelector.recent_executions_for_groups([2, 3]).query
        window = query.annotations['recent_rank']
        self.assertEqual([column.target.name for column in window.partition_by.get_source_expressions()],
                         ['task_group'])
        self.assertEqual([order.expression.target.name for order in window.order_by.get_source_expressions()],
                         ['planned_at', 'id'])
        self.assertTrue(all(order.descending for order in window.order_by.get_source_expressions()))
        self.assertTrue(any(
            getattr(condition, 'rhs', None) == RECENT_EXECUTION_LIMIT
            for condition in query.where.children
        ))
        self.assertEqual(query.order_by, ('task_group_id', '-planned_at', '-id'))

    def test_task_recent_results_default_and_max_follow_display_limit(self):
        self.assertEqual(TaskRecentResultService.normalize_limit(None), RECENT_EXECUTION_LIMIT)
        self.assertEqual(TaskRecentResultService.normalize_limit(100), RECENT_EXECUTION_LIMIT)
