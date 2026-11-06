from time import monotonic
from threading import Event
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.task_center.services.scheduler_readiness import SchedulerReadinessService
from src.processes.scheduler.runner import ScheduleRunner


class SchedulerReadinessTests(SimpleTestCase):
    @patch('src.apps.task_center.services.scheduler_readiness.MonitoringQuerySelector.service_heartbeats')
    @patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.policy')
    @patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.store')
    def test_only_current_container_fresh_cleanup_heartbeat_is_ready(self, store, policy, rows):
        from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
        policy.return_value = DatasourcePerformancePolicy()
        result = rows.return_value.filter.return_value.values.return_value.first
        with patch('src.apps.task_center.services.scheduler_readiness.socket.gethostname', return_value='example-pod'), \
                patch.dict('os.environ', {'MANGO_SERVICE_INSTANCE': 'example-scheduler'}):
            for value in (None, {'metadata': {}}, {'metadata': {'cleanup_consumers_alive': False}},
                          {'metadata': {'cleanup_consumers_alive': True}},
                          {'metadata': {'cleanup_consumers_alive': True, 'cleanup_consumer_threads': 4}}):
                result.return_value = value
                self.assertFalse(SchedulerReadinessService.ready())
            store.assert_not_called()
            result.return_value = {'metadata': {'cleanup_consumers_alive': True, 'cleanup_consumer_threads': 2,
                                              'datasource_maintenance_healthy': False}}
            self.assertFalse(SchedulerReadinessService.ready())
            result.return_value['metadata']['datasource_maintenance_healthy'] = True
            self.assertTrue(SchedulerReadinessService.ready())
            store.return_value.get_entry.assert_called_once_with('health-readonly')
        kwargs = rows.return_value.filter.call_args.kwargs
        self.assertEqual(kwargs['host_name'], 'example-pod')
        self.assertEqual(kwargs['instance_name'], 'example-scheduler')
        self.assertIn('last_seen_at__gte', kwargs)

    def test_live_but_stuck_cleanup_consumers_are_not_ready(self):
        runner = ScheduleRunner(cleanup_only=True)
        runner.cleanup_thread_limit = 2
        runner.cleanup_retire_events = [Event(), Event()]
        runner.cleanup_threads = [Mock(is_alive=Mock(return_value=True)) for _ in range(2)]
        self.assertFalse(runner.is_cleanup_consumers_alive())
        runner.cleanup_activity = [monotonic()] * 2
        self.assertTrue(runner.is_cleanup_consumers_alive())
        runner.cleanup_activity[1] -= 100
        self.assertFalse(runner.is_cleanup_consumers_alive())

    @patch('src.processes.scheduler.runner.threading.Thread')
    @patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.policy')
    def test_configured_thread_count_scales_without_interrupting_inflight_cleanup(self, policy, thread):
        from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
        thread.side_effect = lambda **kwargs: Mock(is_alive=Mock(return_value=True))
        policy.return_value = DatasourcePerformancePolicy()
        runner = ScheduleRunner(cleanup_only=True)
        runner.start_cleanup_consumers()
        self.assertEqual(thread.call_count, 2)
        policy.return_value = DatasourcePerformancePolicy(cleanup_consumer_threads=4)
        runner.start_cleanup_consumers()
        self.assertEqual(thread.call_count, 4)
        original = list(runner.cleanup_threads)
        policy.return_value = DatasourcePerformancePolicy(cleanup_consumer_threads=1)
        runner.start_cleanup_consumers()
        self.assertTrue(all(event.is_set() for event in runner.cleanup_retire_events[1:]))
        for value in original:
            value.join.assert_not_called()
        runner.cleanup_activity[0] = monotonic()
        self.assertTrue(runner.is_cleanup_consumers_alive())
        policy.return_value = DatasourcePerformancePolicy(cleanup_consumer_threads=3)
        runner.start_cleanup_consumers()
        self.assertEqual(thread.call_count, 4, 'retiring workers must finish before replacement')
        self.assertFalse(runner.is_cleanup_consumers_alive())
        for value in original[1:3]:
            value.is_alive.return_value = False
        runner.start_cleanup_consumers()
        self.assertEqual(thread.call_count, 6)
        self.assertTrue(all(not event.is_set() for event in runner.cleanup_retire_events[:3]))
        self.assertTrue(runner.cleanup_retire_events[3].is_set())

    @patch.object(ScheduleRunner, 'recover_inline_cleanup')
    @patch('src.processes.scheduler.runner.ServiceHeartbeatService.beat_if_due')
    @patch.object(ScheduleRunner, 'start_cleanup_consumers')
    @patch.object(ScheduleRunner, 'start_dispatch_consumer')
    @patch.object(ScheduleRunner, 'ensure_dispatch_consumer')
    @patch.object(ScheduleRunner, 'tick')
    def test_cleanup_only_does_not_dispatch_or_trigger_business_jobs(self, tick, ensure, dispatch, cleanup, beat, recovery):
        runner = ScheduleRunner(cleanup_only=True)
        beat.side_effect = lambda *args, **kwargs: runner.stop_event.set()
        runner.run_forever()
        cleanup.assert_called()
        dispatch.assert_not_called()
        ensure.assert_not_called()
        tick.assert_not_called()
        recovery.assert_called_once()
        self.assertTrue(beat.call_args.kwargs['metadata']['cleanup_only'])
