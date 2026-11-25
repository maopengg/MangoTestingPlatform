from datetime import timedelta
from threading import Event
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.utils import timezone

from src.processes.scheduler.runner import ScheduleRunner


class SchedulerMaintenanceTests(SimpleTestCase):
    def test_single_consumer_is_not_restarted_while_blocked_and_stops_before_pools_close(self):
        entered, release = Event(), Event()
        runner = ScheduleRunner(node_name='example-node', cleanup_only=True)

        def blocked():
            entered.set()
            release.wait(2)

        runner.recover_inline_cleanup = Mock(side_effect=blocked)
        with patch('django.db.close_old_connections'), patch('django.db.connections.close_all') as close, \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all') as pools, \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
            runner.start_maintenance_consumer()
            try:
                self.assertTrue(entered.wait(1))
                thread = runner.maintenance_thread
                runner.start_maintenance_consumer()
                self.assertIs(runner.maintenance_thread, thread)
                runner.request_stop()
                pools.assert_not_called()
            finally:
                release.set()
                runner.stop()
            self.assertFalse(thread.is_alive())
            close.assert_called_once()
            pools.assert_called_once()

    def test_blocked_maintenance_cannot_prevent_main_heartbeat_or_business_scans(self):
        entered, release = Event(), Event()
        runner = ScheduleRunner(node_name='example-node', poll_interval=0.001)
        runner.recover_inline_cleanup = Mock()
        runner.run_due_system_jobs = Mock(side_effect=lambda *_: (entered.set(), release.wait(2)))
        runner.tick = Mock()
        beats = []

        def beat(*args, **kwargs):
            self.assertTrue(entered.wait(1))
            beats.append(kwargs['metadata'])
            if len(beats) == 2:
                runner.request_stop()
                release.set()

        with patch('django.db.close_old_connections'), patch('django.db.connections.close_all'), \
                patch.object(runner, 'start_cleanup_consumers'), patch.object(runner, 'start_datasource_recovery'), \
                patch.object(runner, 'start_dispatch_consumer'), patch.object(runner, 'ensure_dispatch_consumer'), \
                patch('src.processes.scheduler.runner.ServiceHeartbeatService.beat_if_due', side_effect=beat), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy'), \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
            try:
                runner.run_forever()
            finally:
                release.set()
                runner.stop()
        self.assertEqual(len(beats), 2)
        self.assertTrue(all(item['maintenance_consumer_alive'] for item in beats))
        self.assertEqual(runner.tick.call_count, 2)
        runner.run_due_system_jobs.assert_called_once()

    def test_maintenance_keeps_lookback_and_cleanup_only_does_not_run_system_jobs(self):
        for cleanup_only in (False, True):
            runner = ScheduleRunner(cleanup_only=cleanup_only, lookback_minutes=2)
            now = timezone.now().replace(second=0, microsecond=0)
            runner.stop_event.wait = Mock(side_effect=lambda *_: runner.stop_event.set())
            runner.recover_inline_cleanup = Mock()
            runner.run_due_system_jobs = Mock()
            with patch('django.db.close_old_connections'), patch('django.db.connections.close_all'), \
                    patch('src.processes.scheduler.runner.timezone.now', return_value=now):
                runner.consume_maintenance()
            runner.recover_inline_cleanup.assert_called_once()
            self.assertEqual([call.args[0] for call in runner.run_due_system_jobs.call_args_list],
                             [] if cleanup_only else [now, now - timedelta(minutes=1)])

    def test_maintenance_failure_is_safe_and_next_cycle_can_continue(self):
        runner = ScheduleRunner(cleanup_only=True)
        runner.recover_inline_cleanup = Mock(side_effect=[OperationalError(1205, 'example-secret'), None])
        waits = []

        def wait(*_):
            waits.append(1)
            if len(waits) == 2:
                runner.stop_event.set()

        runner.stop_event.wait = Mock(side_effect=wait)
        with patch('django.db.close_old_connections'), patch('django.db.connections.close_all'), \
                self.assertLogs('system', level='ERROR') as logs:
            runner.consume_maintenance()
        self.assertEqual(runner.recover_inline_cleanup.call_count, 2)
        self.assertIn('database_code=1205', '\n'.join(logs.output))
        self.assertNotIn('example-secret', '\n'.join(logs.output))
