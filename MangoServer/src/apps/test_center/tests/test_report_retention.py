from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.models import Tasks, ScheduledTaskGroup
from src.apps.task_center.services.selection.recent_results import TaskRecentResultService
from src.apps.task_center.services.scheduling.task_group import ScheduledTaskGroupService
from src.apps.test_center.services.reporting.test_suite.retention import TestSuiteRetentionService


class ReportRetentionTests(SimpleTestCase):
    def test_recent_quality_keeps_success_counts_without_a_report_link(self):
        from django.utils import timezone
        from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
        now = timezone.now()
        suite = {'id': 1, 'tasks_id': 2, 'test_env': 0, 'status': TaskEnum.SUCCESS.value,
                 'create_time': now, 'update_time': now, 'retained_summary': {
                     'execution_summary': TestSuiteSummaryService.effective_summary_from_rows(self.rows())}}
        with patch('src.apps.task_center.services.selection.recent_results.TestSuite') as suites, \
             patch('src.apps.task_center.services.selection.recent_results.TestSuiteDetails') as details:
            suites.objects.filter.return_value.values.return_value.order_by.return_value.iterator.return_value = iter([suite])
            details.objects.filter.return_value.values.return_value = []
            result = TaskRecentResultService.get_recent_results([2])['2'][0]
        self.assertEqual(result['pass_rate'], 100)
        self.assertEqual(result['total'], 3)
        self.assertFalse(result['report_retained'])
        self.assertIsNone(result['test_suite_id'])

    def test_group_sync_preserves_independent_policy(self):
        self.assertNotIn('report_retention_policy', {field.name for field in ScheduledTaskGroup._meta.fields})
        self.assertNotIn('api_concurrency_limit', {field.name for field in ScheduledTaskGroup._meta.fields})
        self.assertIn('api_concurrency_limit', {field.name for field in Tasks._meta.fields})
        self.assertEqual(Tasks._meta.get_field('report_retention_policy').default, 'all')
        for policy in ['all', 'abnormal_only']:
            task = SimpleNamespace(report_retention_policy=policy, save=Mock(),
                                   timing_strategies=Mock(), status=1)
            member = SimpleNamespace(module_id=1, task_id=10, task=task, save=Mock())
            group = SimpleNamespace(id=2, revision=3, timing_strategies=Mock())
            with patch('src.apps.task_center.services.scheduling.task_group.ScheduledTaskGroupModule') as members, \
                 patch.object(ScheduledTaskGroupService, '_task_values', return_value={'name': '测试任务'}):
                members.objects.select_for_update.return_value.filter.return_value.select_related.return_value = [member]
                ScheduledTaskGroupService._sync_members(group, [SimpleNamespace(id=1)], 1,
                    new_task_report_retention_policy='all')
            self.assertEqual(task.report_retention_policy, policy)

    def test_new_group_child_receives_initial_policy_without_group_field(self):
        member = SimpleNamespace(module_id=1, task_id=None, save=Mock())
        group = SimpleNamespace(id=2, revision=3, timing_strategies=Mock(), case_types=[1], case_people_id=1)
        with patch('src.apps.task_center.services.scheduling.task_group.ScheduledTaskGroupModule') as members, \
             patch('src.apps.task_center.services.scheduling.task_group.Tasks') as tasks, \
             patch.object(ScheduledTaskGroupService, '_task_values', return_value={'name': '新子任务'}):
            members.objects.select_for_update.return_value.filter.return_value.select_related.return_value = [member]
            ScheduledTaskGroupService._sync_members(group, [SimpleNamespace(id=1)], 1,
                new_task_report_retention_policy='abnormal_only')
            tasks.objects.create.assert_called_once_with(name='新子任务', case_people_id=1,
                                                        report_retention_policy='abnormal_only')

    def suite(self, **overrides):
        return SimpleNamespace(**{
            'report_retention_policy': ReportRetentionPolicyEnum.ABNORMAL_ONLY.value,
            'status': TaskEnum.SUCCESS.value, 'retained_summary': None, **overrides})

    def rows(self, **overrides):
        return [{'status': TaskEnum.SUCCESS.value, 'success': 3, 'case_sum': 3,
                 'fail': 0, 'warning': 0, 'is_excluded': False, 'failure_reason': '',
                 'failure_description': '', 'error_message': None, **overrides}]

    def test_only_original_clean_success_is_eligible(self):
        self.assertTrue(TestSuiteRetentionService.eligible(self.suite(), self.rows()))
        for field, value in [('fail', 1), ('warning', 1), ('is_excluded', True),
                             ('failure_reason', 'test_case'), ('failure_description', '已排查'),
                             ('error_message', '异常')]:
            with self.subTest(field=field):
                self.assertFalse(TestSuiteRetentionService.eligible(self.suite(), self.rows(**{field: value})))
        for status in [TaskEnum.FAIL.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value,
                       TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value]:
            self.assertFalse(TestSuiteRetentionService.eligible(self.suite(status=status), self.rows()))
            self.assertFalse(TestSuiteRetentionService.eligible(self.suite(), self.rows(status=status)))
        self.assertFalse(TestSuiteRetentionService.eligible(self.suite(report_retention_policy='all'), self.rows()))
        self.assertFalse(TestSuiteRetentionService.eligible(self.suite(), []))

    def test_cleanup_saves_counts_before_deleting_heavy_data_without_changing_execution_time(self):
        with patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuite') as suites, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuiteDetails') as details, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.ExecutionResult') as results, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.default_storage') as storage, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuiteSummaryService.counter_data',
                   return_value={'case_sum': 3, 'success': 3}):
            suites.objects.select_for_update.return_value.filter.return_value.first.return_value = self.suite()
            details.objects.filter.return_value.values.return_value = self.rows()
            results.objects.filter.return_value.exclude.return_value.values_list.return_value = ['result/report.json']
            cleanup = TestSuiteRetentionService.cleanup.__wrapped__
            self.assertTrue(cleanup(TestSuiteRetentionService, 1))
            storage.delete.assert_called_once_with('result/report.json')
            summary = suites.objects.filter.return_value.update.call_args.kwargs
            self.assertEqual(set(summary), {'retained_summary', 'report_retained'})
            self.assertFalse(summary['report_retained'])
            self.assertEqual(summary['retained_summary']['execution_summary']['success'], 3)
            details.objects.filter.return_value.delete.assert_called_once()

    def test_storage_failure_does_not_delete_report_rows(self):
        with patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuite') as suites, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuiteDetails') as details, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.ExecutionResult') as results, \
             patch('src.apps.test_center.services.reporting.test_suite.retention.default_storage.delete', side_effect=OSError), \
             patch('src.apps.test_center.services.reporting.test_suite.retention.TestSuiteSummaryService.counter_data', return_value={}):
            suites.objects.select_for_update.return_value.filter.return_value.first.return_value = self.suite()
            details.objects.filter.return_value.values.return_value = self.rows()
            results.objects.filter.return_value.exclude.return_value.values_list.return_value = ['result/report.json']
            with self.assertRaises(OSError):
                TestSuiteRetentionService.cleanup.__wrapped__(TestSuiteRetentionService, 1)
            details.objects.filter.return_value.delete.assert_not_called()
            suites.objects.filter.return_value.update.assert_not_called()

    def test_group_child_can_only_override_policy_not_group_owned_content(self):
        serializer = TasksSerializers(instance=Tasks(task_group_id=1))
        attrs = {'report_retention_policy': 'abnormal_only', 'update_user': Mock()}
        self.assertEqual(serializer.validate(attrs), attrs)
        with self.assertRaises(TaskCenterError):
            serializer.validate({**attrs, 'name': '不能绕过任务组修改'})
        invalid = TasksSerializers(instance=Tasks(task_group_id=1), data={'report_retention_policy': 'invalid'}, partial=True)
        self.assertFalse(invalid.is_valid())
