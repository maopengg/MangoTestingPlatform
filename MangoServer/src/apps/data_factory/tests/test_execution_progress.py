from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.selectors.execution_progress import DatasourceExecutionProgressSelector as Operations
from src.apps.data_factory.services.reporting.execution_progress import DatasourceExecutionProgressService as Progress
from src.apps.auto_api.selectors.execution_efficiency import ApiExecutionEfficiencySelector as Steps


class ExecutionProgressTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.since = self.now - timedelta(seconds=60)
        self.owners = [{'detail_id': 10, 'attempt': 3, 'started_at': self.since, 'report_id': 100}]

    def test_operations_and_completed_steps_are_merged_without_changing_results(self):
        with patch.object(Operations, 'latest_successful_operations', return_value={10: self.now}), \
                patch.object(Steps, 'latest_step_activity', return_value={10: self.since}):
            values = Progress.latest(self.owners, self.since)
        aware = timezone.make_aware(self.now, timezone.get_default_timezone()) if timezone.is_naive(self.now) else self.now
        self.assertEqual(values, {10: aware.timestamp()})

    def test_no_live_owner_does_not_scan_audit_tables(self):
        with patch.object(Operations, 'latest_successful_operations') as query:
            self.assertEqual(Progress.latest([], self.since), {})
        query.assert_not_called()

    def test_diagnostic_database_failure_is_not_a_case_error_or_a_false_healthy_signal(self):
        with patch.object(Operations, 'latest_successful_operations', side_effect=OSError('AUTO unavailable')):
            self.assertIsNone(Progress.latest(self.owners, self.since))

    def test_operation_query_is_bounded_and_preserves_attempt_and_cleanup_owner(self):
        factory, audits = Mock(), Mock()
        factory.alias.return_value.filter.return_value.filter.return_value.annotate.return_value.values_list.return_value = [
            (50, 10)]
        rows = audits.filter.return_value.exclude.return_value.order_by.return_value.values.return_value
        rows.annotate.return_value = [{'source_detail__case_detail_id': None,
                                     'source_detail__execution_id': 50, 'latest': self.now}]
        with patch('src.apps.data_factory.selectors.execution_progress.DataFactoryExecution',
                   SimpleNamespace(objects=factory)), \
                patch('src.apps.data_factory.selectors.execution_progress.SqlExecutionRecord',
                      SimpleNamespace(objects=audits)):
            self.assertEqual(Operations.latest_successful_operations(self.owners, self.since), {10: self.now})
        condition = str(audits.filter.call_args.args[0])
        self.assertIn('case_detail_id', condition)
        self.assertIn('case_attempt', condition)
        self.assertIn('execution_id', condition)
        self.assertEqual(audits.filter.call_args.kwargs, {'status': 'success', 'create_time__gte': self.since})
        audits.filter.return_value.exclude.assert_called_once_with(
            source_stage__in=['connect', 'test_connection', 'network_probe'])
        owner_query = str(factory.alias.return_value.filter.call_args.args[0])
        self.assertIn('parent_attempt', owner_query)
        self.assertIn('parent_case_detail_id', owner_query)

    def test_owner_uses_immutable_dispatch_time_not_renewed_heartbeat(self):
        from src.apps.test_center.selectors.report_progress import ReportProgressSelector
        rows = Mock()
        rows.filter.return_value = rows
        rows.order_by.return_value.values.return_value = [{
            'id': 10, 'retry': 3, 'test_suite_id': 100, 'push_time': self.now,
            'summary_data__meta__dispatch_started_at': self.since.isoformat(),
        }]
        with patch('src.apps.test_center.selectors.report_progress.TestSuiteDetails',
                   SimpleNamespace(objects=rows)):
            owners = ReportProgressSelector.running_owners(attempts={10: 3})
        self.assertEqual(owners[0]['started_at'], self.since)
        self.assertNotEqual(owners[0]['started_at'], self.now)
        self.assertEqual(owners[0]['attempt'], 3)

    def test_latest_steps_ignore_older_trace_even_if_it_finishes_late(self):
        traces, steps = Mock(), Mock()
        traces.filter.return_value.order_by.return_value.values.return_value = [
            {'id': 102, 'test_suite_detail_id': 10}, {'id': 101, 'test_suite_detail_id': 10}]
        rows = steps.filter.return_value.order_by.return_value.values.return_value
        rows.annotate.return_value = [{'trace_id': 102, 'latest': self.now}]
        with patch('src.apps.auto_api.selectors.execution_efficiency.ApiCaseExecutionTrace',
                   SimpleNamespace(objects=traces)), \
                patch('src.apps.auto_api.selectors.execution_efficiency.ApiCaseExecutionStep',
                      SimpleNamespace(objects=steps)):
            self.assertEqual(Steps.latest_step_activity(self.owners, self.since), {10: self.now})
        selected = steps.filter.call_args.kwargs
        self.assertEqual(set(selected['trace_id__in']), {102})
        self.assertEqual(selected['finished_at__gte'], self.since)
        bound = str(traces.filter.call_args.args[0])
        self.assertIn('started_at__gte', bound)
