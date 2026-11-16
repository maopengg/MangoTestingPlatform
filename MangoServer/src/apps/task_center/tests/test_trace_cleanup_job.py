from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.auto_api.services.execution_trace.retention import ApiTraceRetentionService as Retention
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.processes.scheduler.system_jobs import SchedulerSystemJobService as Jobs


class TraceCleanupJobTests(SimpleTestCase):
    def test_bounded_cleanup_continues_hourly_with_unchanged_retention(self):
        self.assertEqual(SystemJobService.get_job('clean_api_case_execution_traces').cron, '15 * * * *')
        with patch.object(Jobs, 'retention_days', return_value=30), \
                patch.object(Retention, 'cleanup', return_value={'deleted_count': 500, 'batches': 1, 'has_more': True}) as cleanup:
            before = timezone.now()
            result = Jobs.clean_api_case_execution_traces.__wrapped__(Jobs)
        self.assertEqual(result, {'retention_days': 30, 'deleted_count': 500, 'batches': 1, 'has_more': True})
        self.assertGreaterEqual(cleanup.call_args.args[0], before - timedelta(days=30))

    def test_budget_exhaustion_returns_remaining_work_not_an_unbounded_loop(self):
        with patch.object(Retention, 'delete_batch', return_value=1) as delete, \
                patch.object(Retention, 'eligible') as rows, patch.object(Retention, 'MAX_BATCHES', 2):
            rows.return_value.exists.return_value = True
            result = Retention.cleanup(timezone.now())
        self.assertEqual(delete.call_count, 2)
        self.assertTrue(result['has_more'])
