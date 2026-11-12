from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.processes.scheduler.system_jobs import SchedulerSystemJobService, subtract_calendar_months


class SqlExecutionCleanupTests(SimpleTestCase):
    def test_calendar_month_subtraction_clamps_month_end(self):
        value = timezone.make_aware(datetime(2024, 3, 31, 12, 30, 45))

        result = subtract_calendar_months(value, 1)

        self.assertEqual(result, timezone.make_aware(datetime(2024, 2, 29, 12, 30, 45)))

    def test_system_job_is_registered(self):
        job = SystemJobService.get_job('clean_sql_execution_records')

        self.assertIsNotNone(job)
        self.assertEqual(job.cron, '45 0 * * *')
        self.assertEqual(job.handler, SchedulerSystemJobService.clean_sql_execution_records)

    @patch.object(SchedulerSystemJobService, 'retention_days', return_value=45)
    @patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.cleanup_expired', return_value=7)
    def test_cleanup_uses_configured_retention_days(self, cleanup_expired, retention_days):
        before = timezone.now()

        result = SchedulerSystemJobService.clean_sql_execution_records.__wrapped__(
            SchedulerSystemJobService,
        )

        after = timezone.now()
        cutoff = cleanup_expired.call_args.args[0]
        self.assertGreaterEqual(cutoff, before - timedelta(days=45))
        self.assertLessEqual(cutoff, after - timedelta(days=45))
        retention_days.assert_called_once_with('SQL_EXECUTION_RETENTION_DAYS')
        self.assertEqual(result['retention_days'], 45)
        self.assertEqual(result['deleted_count'], 7)
