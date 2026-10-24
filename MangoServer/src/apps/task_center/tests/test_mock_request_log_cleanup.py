from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.processes.scheduler.system_jobs import SchedulerSystemJobService


class MockRequestLogCleanupTests(SimpleTestCase):
    def test_system_job_is_registered(self):
        job = SystemJobService.get_job('clean_mock_request_logs')

        self.assertIsNotNone(job)
        self.assertEqual(job.cron, '40 2 * * *')
        self.assertEqual(job.handler, SchedulerSystemJobService.clean_mock_request_logs)

    @patch(
        'src.apps.auto_api.services.mock_log_cleanup.MockRequestLogCleanupService.cleanup_before',
        return_value=17,
    )
    @patch.object(SchedulerSystemJobService, 'retention_days', return_value=21)
    def test_cleanup_uses_configured_retention_days(self, retention_days, cleanup_before):
        before = timezone.now()

        result = SchedulerSystemJobService.clean_mock_request_logs.__wrapped__(
            SchedulerSystemJobService,
        )

        after = timezone.now()
        cutoff_time = cleanup_before.call_args.args[0]
        self.assertGreaterEqual(cutoff_time, before - timedelta(days=21))
        self.assertLessEqual(cutoff_time, after - timedelta(days=21))
        retention_days.assert_called_once_with('MOCK_REQUEST_LOG_RETENTION_DAYS')
        self.assertEqual(result['retention_days'], 21)
        self.assertEqual(result['deleted_count'], 17)
