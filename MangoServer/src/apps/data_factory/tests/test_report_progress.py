from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService as Health
from src.apps.data_factory.services.reporting.report_progress import DatasourceReportProgressService as Progress
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class ReportProgressTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.snapshot = {'test_suite_id': 100, 'terminal_count': 3, 'running_count': 2, 'pending_count': 5}
        for guard in (patch.object(Governor, 'store', return_value=self.store),
                      patch.object(Health, 'safe_observe')):
            guard.start()
            self.addCleanup(guard.stop)

    def test_other_report_completions_and_heartbeat_do_not_mask_stall(self):
        Progress.observe(self.snapshot)
        self.store.now += 301
        Progress.observe({**self.snapshot, 'test_suite_id': 200, 'terminal_count': 50})
        Progress.observe(self.snapshot)
        self.assertTrue(Health.safe_observe.call_args.kwargs['active'])
        self.assertEqual(Health.safe_observe.call_args.kwargs['metrics']['no_completion_seconds'], 301)

    def test_real_completion_and_retry_reset_diagnostic_without_marking_case(self):
        Progress.observe(self.snapshot)
        self.store.now += 301
        for count in (4, 0):
            Progress.observe({**self.snapshot, 'terminal_count': count})
            self.assertFalse(Health.safe_observe.call_args.kwargs['active'])
            self.assertEqual(Health.safe_observe.call_args.kwargs['metrics']['no_completion_seconds'], 0)

    def test_finished_report_closes_incident_and_removes_only_its_baseline(self):
        Progress.observe(self.snapshot)
        Progress.observe({**self.snapshot, 'test_suite_id': 200})
        self.store.now += 301
        Progress.observe({**self.snapshot, 'running_count': 0, 'pending_count': 0})
        self.assertFalse(Health.safe_observe.call_args.kwargs['active'])
        self.assertNotIn('report-progress:100', self.store.values)
        self.assertIn('report-progress:200', self.store.values)

    def test_large_case_real_operation_progress_prevents_false_alarm_without_hiding_stall(self):
        Progress.observe(self.snapshot)
        self.store.now += 301
        activity = self.store.now - 5
        Progress.observe({**self.snapshot, 'last_activity_at': activity})
        self.assertFalse(Health.safe_observe.call_args.kwargs['active'])
        metrics = Health.safe_observe.call_args.kwargs['metrics']
        self.assertEqual(metrics['no_completion_seconds'], 301)
        self.assertEqual(metrics['no_progress_seconds'], 5)
        self.store.now += 301
        Progress.observe({**self.snapshot, 'last_activity_at': activity})
        self.assertTrue(Health.safe_observe.call_args.kwargs['active'])

    def test_unavailable_diagnostic_does_not_close_incident_or_change_results(self):
        Progress.observe(self.snapshot)
        self.store.now += 301
        Health.safe_observe.reset_mock()
        Progress.observe({**self.snapshot, 'activity_evidence_available': False})
        Health.safe_observe.assert_not_called()
        Progress.observe({**self.snapshot, 'activity_evidence_available': False,
                          'running_count': 0, 'pending_count': 0})
        self.assertFalse(Health.safe_observe.call_args.kwargs['active'])

    def test_monitor_uses_only_activity_from_the_same_report_and_attempts(self):
        from src.apps.test_center.selectors.report_progress import ReportProgressSelector
        from src.apps.data_factory.services.reporting.execution_progress import DatasourceExecutionProgressService
        Progress.observe(self.snapshot)
        Progress.observe({**self.snapshot, 'test_suite_id': 200})
        self.store.now += 301
        self.store.scan = Mock(return_value={'items': [], 'next_cursor': None})
        owners = [{'detail_id': 10, 'attempt': 1, 'report_id': 100},
                  {'detail_id': 20, 'attempt': 3, 'report_id': 200}]
        with patch.object(ReportProgressSelector, 'active_ids', return_value=[100, 200]), \
                patch.object(ReportProgressSelector, 'running_owners', return_value=owners), \
                patch.object(ReportProgressSelector, 'snapshots', return_value=[
                    self.snapshot, {**self.snapshot, 'test_suite_id': 200}]), \
                patch.object(DatasourceExecutionProgressService, 'latest',
                             return_value={20: self.store.now - 2}) as latest:
            Progress.scheduled_monitor()
        latest.assert_called_once()
        self.assertEqual(latest.call_args.args[0], owners)
        calls = Health.safe_observe.call_args_list[-2:]
        self.assertEqual(calls[0].args[0], 'api-report:100')
        self.assertTrue(calls[0].kwargs['active'])
        self.assertFalse(calls[1].kwargs['active'])
