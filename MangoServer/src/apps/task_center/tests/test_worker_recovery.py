from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from concurrent.futures import Future

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
from src.apps.task_center.services.execution.claim import ApiTaskClaimService
from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService as Recovery
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import Project, ProjectProduct, TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService as Infrastructure
from src.apps.user.models import User


class ProcessIdentityTests(SimpleTestCase):
    def setUp(self):
        policy = patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy')
        policy.start()
        self.addCleanup(policy.stop)
        guard = patch('src.apps.data_factory.services.recovery.health_incident.DatasourceHealthIncidentService.safe_observe')
        self.health = guard.start()
        self.addCleanup(guard.stop)
        progress = patch('src.apps.data_factory.services.reporting.execution_progress.'
                         'DatasourceExecutionProgressService.for_attempts', return_value={})
        self.activity = progress.start()
        self.addCleanup(progress.stop)

    def test_long_factory_operation_progress_does_not_raise_no_completion_alarm(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        future = Future()
        futures = {future: SimpleNamespace(test_suite=1, test_suite_details=2, case_id=3, attempt=4)}
        wall = timezone.now()
        stamp = (timezone.make_aware(wall, timezone.get_default_timezone())
                 if timezone.is_naive(wall) else wall).timestamp()
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=0):
            runner.execution_progress(futures)
        self.activity.return_value = {2: stamp - 2}
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=601), \
                patch('django.utils.timezone.now', return_value=wall):
            values = runner.execution_progress(futures)
        self.assertEqual(values['no_completion_seconds'], 601)
        self.assertEqual(values['no_progress_seconds'], 2)
        self.assertFalse(self.health.call_args.kwargs['active'])
        self.assertFalse(future.done())
        self.assertEqual(self.activity.call_args.args[0], {2: 4})

    def test_progress_query_failure_does_not_break_worker_and_idle_resolves_incident(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        future = Future()
        futures = {future: SimpleNamespace(test_suite=1, test_suite_details=2, case_id=3, attempt=1)}
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=0):
            runner.execution_progress(futures)
        self.activity.return_value = None
        self.health.reset_mock()
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=61):
            runner.execution_progress(futures)
        self.health.assert_not_called()
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=80):
            runner.execution_progress({})
        self.assertFalse(self.health.call_args.kwargs['active'])

    def test_no_completion_warning_is_visible_without_debug_and_never_changes_results(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        future = Future()
        futures = {future: SimpleNamespace(test_suite=1, test_suite_details=2, case_id=3, attempt=1)}
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=0):
            runner.execution_progress(futures)
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=61), \
                self.assertLogs('api', level='WARNING') as captured:
            values = runner.execution_progress(futures)
            runner.execution_progress(futures)
        self.assertEqual(len(captured.output), 1)
        self.assertEqual(values['no_completion_seconds'], 61)
        self.assertFalse(future.done())
        future.set_result(None)
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=62):
            values = runner.execution_progress(futures)
        self.assertEqual(values['no_completion_seconds'], 0)
        self.assertEqual(values['completed_waiting_settlement'], 1)

    def test_completion_between_heartbeats_is_observed_before_future_is_removed(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        runner.running, runner.poll_interval = True, 0.1
        runner.thread_pool_size = runner.executor_size = 2
        runner.last_recovery_at = float('inf')
        runner.refresh_thread_pool_size = Mock()
        runner.db_context_registry, runner.executor = Mock(), Mock()
        first, second = Future(), Future()
        runner.executor.submit.side_effect = [first, second]
        runner.can_claim = Mock(side_effect=[True, True, False])
        runner.claim = Mock(return_value=SimpleNamespace(test_suite=1, test_suite_details=2, case_id=3, attempt=1))
        clock, observations = [0], []
        def heartbeat(futures):
            observations.append(runner.execution_progress(futures)['no_completion_seconds'])
            if len(observations) == 2:
                runner.stop()
        runner.report_heartbeat = Mock(side_effect=heartbeat)
        def complete(futures, **kwargs):
            if not first.done():
                clock[0] = 61
                first.set_result(None)
                return {first}, {second}
            clock[0] = 62
            second.set_result(None)
            return {second}, set()
        with patch('src.processes.api_worker.runner.time.monotonic', side_effect=lambda: clock[0]), \
                patch('src.processes.api_worker.runner.wait', side_effect=complete), \
                patch.object(Recovery, 'finish_unreported', return_value=False), \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
            runner.run_forever()
        self.assertEqual(observations, [0, 0])
        self.assertEqual(runner.executor.submit.call_count, 2)
        self.assertEqual(runner.claim.call_count, 2)
        self.assertEqual(runner._last_completion_at, 62)

    def test_same_completed_future_during_settlement_outage_does_not_reset_progress_forever(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        future = Future()
        future.set_result(None)
        futures = {future: SimpleNamespace(test_suite=1, test_suite_details=2, case_id=3, attempt=1)}
        runner.observe_completions({future}, now=10)
        with patch('src.processes.api_worker.runner.time.monotonic', return_value=71), \
                self.assertLogs('api', level='WARNING'):
            runner.observe_completions({future})
            values = runner.execution_progress(futures)
        self.assertEqual(values['no_completion_seconds'], 61)
        self.assertEqual(values['completed_waiting_settlement'], 1)

    def test_fast_completion_resets_stall_diagnostic_without_altering_running_case(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name = 'AUTO_WORKER'
        runner._last_completion_at, runner._stalled_logged_at = 0, 60
        finished, active = Future(), Future()
        finished.set_exception(RuntimeError('AUTO_EXPECTED_FAILURE'))
        with self.assertLogs('api', level='INFO') as logs:
            runner.observe_completions({finished}, now=70)
        self.assertIn('api_worker_execution_progress_restored', logs.output[0])
        self.assertFalse(active.done())
        self.assertIsNone(runner._stalled_logged_at)
        self.assertEqual(runner._last_completion_at, 70)

    def test_resource_wait_does_not_expand_worker_case_concurrency(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.thread_pool_size = runner.executor_size = 1
        first = Future()
        self.assertFalse(runner.can_claim({first: None}))
        first._mango_resource_parked = True
        self.assertFalse(runner.can_claim({first: None}))
        self.assertTrue(runner.can_claim({}))
        second = Future()
        self.assertFalse(runner.can_claim({first: None, second: None}))
        self.assertFalse(first.done())

    def test_invalid_upgrade_policy_prevents_claiming_any_case(self):
        from src.processes.api_worker.runner import ApiWorkerRunner
        from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_POLICY_INVALID
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.claim = Mock()
        runner.executor = Mock()
        runner.db_context_registry = Mock()
        with patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                   side_effect=DataFactoryError(DATASOURCE_POLICY_INVALID)), \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'), \
                self.assertRaises(DataFactoryError):
            runner.run_forever()
        runner.claim.assert_not_called()
        runner.executor.shutdown.assert_called_once_with(wait=True)
        runner.db_context_registry.close_all.assert_called_once()

    def test_replaced_worker_progress_incident_closes_only_after_all_old_slots_are_isolated(self):
        now = timezone.now()
        owner = {'worker_name': 'worker-0', 'process_token': 'a' * 32}
        row = {'id': 7, 'retry': 2, 'push_time': now - timedelta(minutes=2), 'worker_owner': owner}
        query = Mock()
        for name in ('filter', 'exclude', 'annotate', 'order_by', 'values'):
            getattr(query, name).return_value = query
        heartbeat = SimpleNamespace(instance_name='worker-0')
        for remaining in (True, False):
            with self.subTest(remaining=remaining), \
                    patch('src.apps.task_center.services.execution.worker_recovery.TestCenterQuerySelector.test_suite_details',
                          return_value=query), \
                    patch('src.apps.task_center.services.execution.worker_recovery.ServiceHeartbeatService.get_online_instances',
                          return_value=[heartbeat]), \
                    patch.object(Recovery, 'replacement_confirmed', return_value=True), \
                    patch.object(Infrastructure, 'block', return_value=True) as block:
                query.iterator.return_value = iter([row])
                query.exists.return_value = remaining
                self.health.reset_mock()
                self.assertEqual(Recovery.recover(), 1)
                block.assert_called_once_with(7, 2, [], expected_push_time=row['push_time'],
                    interruption_reason='执行进程已重启或被替换，本次执行未完成。请核查已发送请求及数据清理状态')
                if remaining:
                    self.health.assert_not_called()
                else:
                    self.health.assert_called_once_with('api-worker:worker-0:' + 'a' * 32,
                                                        worker=True, active=False, metrics={})

    def test_stable_identity_changes_after_fork_and_does_not_expose_credentials(self):
        with patch.object(RuntimeProcessIdentity, '_pid', None), \
                patch.object(RuntimeProcessIdentity, '_identity', None), \
                patch('src.apps.system.services.runtime_center.process_identity.os.getpid', return_value=100) as pid:
            first = RuntimeProcessIdentity.current()
            self.assertEqual(first, RuntimeProcessIdentity.current())
            pid.return_value = 101
            self.assertNotEqual(first['process_token'], RuntimeProcessIdentity.current()['process_token'])
            self.assertEqual(set(first), {'process_token', 'process_started_at'})

    def test_same_process_slow_case_and_recent_replacement_are_not_fenced(self):
        now = timezone.now()
        heartbeat = SimpleNamespace(status=1, last_seen_at=now, metadata={
            'process_token': 'a' * 32, 'process_started_at': (now - timedelta(minutes=1)).isoformat()})
        self.assertFalse(Recovery.replacement_confirmed(
            {'process_token': 'a' * 32}, heartbeat, now - timedelta(hours=5), now))
        heartbeat.metadata['process_token'] = 'b' * 32
        heartbeat.metadata['process_started_at'] = (now - timedelta(seconds=10)).isoformat()
        self.assertFalse(Recovery.replacement_confirmed({}, heartbeat, now - timedelta(hours=5), now))
        heartbeat.metadata['process_started_at'] = 'invalid'
        self.assertFalse(Recovery.replacement_confirmed({}, heartbeat, now - timedelta(hours=5), now))

    def test_execution_end_recovery_requires_matching_replaced_process_not_just_elapsed_time(self):
        now = timezone.now()
        heartbeat = SimpleNamespace(instance_name='AUTO_WORKER', status=1, last_seen_at=now,
            metadata={'process_token': 'b'*32, 'process_started_at': (now - timedelta(minutes=2)).isoformat()})
        with patch('src.apps.task_center.services.execution.worker_recovery.ServiceHeartbeatService.get_online_instances',
                   return_value=[heartbeat]):
            self.assertTrue(Recovery.execution_owner_replaced('AUTO_WORKER', {'process_token': 'a'*32},
                            now - timedelta(hours=1)))
            self.assertFalse(Recovery.execution_owner_replaced('OTHER_WORKER', {'process_token': 'a'*32},
                             now - timedelta(hours=1)))
            self.assertFalse(Recovery.execution_owner_replaced('AUTO_WORKER', {'process_token': 'b'*32},
                             now - timedelta(hours=1)))
            self.assertFalse(Recovery.execution_owner_replaced('AUTO_WORKER', {}, now - timedelta(hours=1)))

    def test_finished_future_control_disconnect_keeps_receipt_without_executing_case_again(self):
        from django.db import OperationalError
        from src.processes.api_worker.runner import ApiWorkerRunner
        future = Future()
        future.set_result(None)
        futures = {future: SimpleNamespace(test_suite_details=7, attempt=2)}
        with patch.object(Recovery, 'finish_unreported', side_effect=[OperationalError(2013, 'AUTO_CLOSED'), False]), \
                patch('src.processes.api_worker.runner.connection.close'), \
                patch.object(ApiWorkerRunner, 'execute') as execute:
            self.assertEqual(ApiWorkerRunner.settle_finished(futures, {future}), 0)
            self.assertIn(future, futures)
            self.assertEqual(ApiWorkerRunner.settle_finished(futures, {future}), 1)
            self.assertFalse(futures)
        execute.assert_not_called()

    def test_sigterm_stops_claiming_but_does_not_cancel_execution(self):
        import signal
        from src.apps.task_center.management.commands.run_api_worker import Command
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = Mock()
        handlers = {}
        with patch('src.apps.task_center.management.commands.run_api_worker.ApiWorkerRunner', return_value=runner), \
                patch('src.apps.task_center.management.commands.run_api_worker.signal.getsignal', return_value=signal.SIG_DFL), \
                patch('src.apps.task_center.management.commands.run_api_worker.signal.signal',
                      side_effect=lambda name, handler: handlers.update({name: handler})):
            runner.run_forever.side_effect = lambda: handlers[signal.SIGTERM](signal.SIGTERM, None)
            Command().handle(concurrency=None, thread_pool_size=10, worker_name='worker-0', lease_seconds=None,
                             poll_interval=3, db_idle_seconds=1800, config_refresh_interval=10)
        runner.stop.assert_called_once()
        runner.executor.shutdown.assert_not_called()
        self.assertEqual(handlers[signal.SIGTERM], signal.SIG_DFL)
        actual = ApiWorkerRunner.__new__(ApiWorkerRunner)
        actual.running = True
        actual.stop()
        self.assertFalse(actual.running)

    def test_scheduler_shutdown_waits_for_current_cleanup_phase_before_closing_pools(self):
        import threading
        from src.processes.scheduler.runner import ScheduleRunner
        runner = ScheduleRunner.__new__(ScheduleRunner)
        runner.running = True
        runner.stop_event = threading.Event()
        runner.dispatch_wakeup_event = threading.Event()
        cleanup = Mock()
        cleanup.is_alive.return_value = True
        runner.cleanup_threads = [cleanup]
        runner.dispatch_consumer_thread = None
        with patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all') as sql, \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all') as protocol:
            cleanup.join.side_effect = lambda: self.assertFalse(sql.called or protocol.called)
            runner.stop()
        cleanup.join.assert_called_once_with()
        self.assertTrue(runner.stop_event.is_set())
        self.assertFalse(runner.running)
        sql.assert_called_once()
        protocol.assert_called_once()

    def test_completed_future_recovery_backs_off_during_control_outage_without_reclaiming(self):
        import time
        from django.db import OperationalError
        from src.processes.api_worker.runner import ApiWorkerRunner
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.worker_name, runner.thread_pool_size = 'worker-0', 10
        runner.running, runner.poll_interval = True, 0.1
        runner.last_recovery_at = time.monotonic() + 60
        runner.refresh_thread_pool_size = Mock()
        runner.current_claim_limit = Mock(return_value=1)
        runner.db_context_registry = Mock()
        runner.executor = Mock()
        future = Future()
        future.set_result(None)
        runner.executor.submit.return_value = future
        runner.claim = Mock(return_value=SimpleNamespace(test_suite_details=7, attempt=2))
        beats = 0
        def heartbeat(_):
            nonlocal beats
            beats += 1
            if beats == 2:
                runner.stop()
        runner.report_heartbeat = Mock(side_effect=heartbeat)
        with patch.object(Recovery, 'finish_unreported', side_effect=[OperationalError(2013, 'AUTO_CONTROL_LOST'), False]), \
                patch('src.processes.api_worker.runner.connection.close'), \
                patch('src.processes.api_worker.runner.time.sleep') as sleep, \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
            runner.run_forever()
        runner.claim.assert_called_once()
        runner.executor.submit.assert_called_once()
        sleep.assert_called_once_with(0.1)


class WorkerReplacementRecoveryTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='Worker恢复测试项目')
        product = ProjectProduct.objects.create(project=project, name='隔离服务')
        user = User.objects.create(name='恢复测试用户', username='worker_recovery_user', password='test-only')
        self.suite = TestSuite.objects.create(id=900001, project_product=product, user=user,
            test_env=0, status=3, is_notice=0, api_concurrency_limit=1)
        self.now = timezone.now()
        self.owner = {'worker_name': 'worker-0', 'process_token': 'a' * 32,
                      'process_started_at': (self.now - timedelta(hours=1)).isoformat()}
        self.detail = TestSuiteDetails.objects.create(test_suite=self.suite, project_product=product,
            type=TestCaseTypeEnum.API.value, test_env=0, case_id=100, case_name='失联执行',
            status=3, retry=1, push_time=self.now - timedelta(minutes=10),
            summary_data={'children': [], 'meta': {'worker_owner': self.owner}})
        self.pending = TestSuiteDetails.objects.create(test_suite=self.suite, project_product=product,
            type=TestCaseTypeEnum.API.value, test_env=0, case_id=101, case_name='正常待执行', status=2, retry=0)
        self.heartbeat = SimpleNamespace(instance_name='worker-0', status=1, last_seen_at=self.now,
            metadata={'process_token': 'b' * 32,
                      'process_started_at': (self.now - timedelta(minutes=2)).isoformat()})
        self.beat_patch = patch('src.apps.task_center.services.execution.worker_recovery.'
            'ServiceHeartbeatService.get_online_instances', return_value=[self.heartbeat])
        self.beat_patch.start()
        self.addCleanup(self.beat_patch.stop)

    def test_replacement_fences_old_attempt_and_next_pending_case_can_be_claimed(self):
        self.assertEqual(Recovery.recover(), 1)
        self.detail.refresh_from_db()
        self.assertTrue(Infrastructure.is_blocked(self.detail.summary_data))
        self.assertEqual((self.detail.status, self.detail.success, self.detail.fail), (TaskEnum.FAIL.value, 0, 0))
        with patch.object(ApiTaskClaimService, 'platform_claim_lock') as lock, \
                patch('src.apps.task_center.services.execution.claim.ApiConcurrencyService.platform_limit', return_value=10):
            lock.return_value.__enter__.return_value = True
            command = ApiTaskClaimService.claim(worker_owner={**self.owner, 'process_token': 'b' * 32})
        self.assertEqual(command.test_suite_details, self.pending.id)
        self.assertEqual(Recovery.recover(), 0)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.retry, 1)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.summary_data['meta']['worker_owner']['process_token'], 'b' * 32)

    def test_current_process_offline_heartbeat_and_recent_claim_are_preserved(self):
        self.heartbeat.metadata['process_token'] = 'a' * 32
        self.assertEqual(Recovery.recover(), 0)
        self.heartbeat.metadata['process_token'] = 'b' * 32
        self.heartbeat.last_seen_at = self.now - timedelta(minutes=10)
        self.assertEqual(Recovery.recover(), 0)
        self.heartbeat.last_seen_at = self.now
        self.detail.push_time = self.now
        self.detail.save(update_fields=['push_time'])
        self.assertEqual(Recovery.recover(), 0)

    def test_scan_then_renew_race_cannot_fence_a_live_owner(self):
        old = self.detail.push_time
        TestSuiteDetails.objects.filter(id=self.detail.id).update(push_time=self.now)
        self.assertFalse(Infrastructure.block(self.detail.id, 1, [], expected_push_time=old))
        self.detail.refresh_from_db()
        self.assertFalse(Infrastructure.is_blocked(self.detail.summary_data))

    def test_progress_writes_preserve_worker_owner_and_blocked_state(self):
        Recovery.recover()
        Results.save_detail_summary(self.detail, [], {'other': 'snapshot'})
        self.detail.refresh_from_db()
        meta = self.detail.summary_data['meta']
        self.assertEqual(meta['worker_owner'], self.owner)
        self.assertTrue(Infrastructure.is_blocked(self.detail.summary_data))

    def test_finished_without_report_result_is_fenced_not_left_using_suite_capacity(self):
        self.assertTrue(Recovery.finish_unreported(self.detail.id, 1))
        self.assertFalse(Recovery.finish_unreported(self.detail.id, 1))
        self.assertFalse(Recovery.finish_unreported(self.detail.id, 2))
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.fail, 0)
        self.assertTrue(Infrastructure.is_blocked(self.detail.summary_data))

    def test_legacy_trace_is_matched_to_current_claim_not_case_or_old_attempt(self):
        self.detail.summary_data = None
        self.detail.save(update_fields=['summary_data'])
        with patch('src.apps.task_center.services.execution.worker_recovery.ApiQuerySelector.'
                   'api_case_execution_trace') as traces:
            traces.return_value.filter.return_value.order_by.return_value.only.return_value.first.return_value = SimpleNamespace(
                worker_name='worker-0')
            self.assertEqual(Recovery.recover(), 1)
        traces.return_value.filter.assert_called_once_with(
            test_suite_detail_id=self.detail.id, started_at__gte=self.detail.push_time, status=3)

    def test_no_fixture_rows_skipped_cleanup_does_not_prevent_review(self):
        from src.apps.data_factory.constants import CLEANUP_REPORT_CONTEXT_KEY
        from src.apps.data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        execution = DataFactoryExecution.objects.create(execution_no='AUTO_EMPTY_EXECUTION',
            project_product_id=self.detail.project_product_id, status=0, cleanup_status=3,
            context={CLEANUP_REPORT_CONTEXT_KEY: {'parent_case_detail_id': self.detail.id, 'parent_attempt': 1}})
        with patch('src.apps.data_factory.services.execution_capacity.DatasourceExecutionCapacityService.'
                   'targets_by_scope', return_value={(self.detail.project_product_id, 0): {}}), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy'):
            self.assertTrue(DatasourceInfrastructureService.review_ready(self.detail))
            item = DataFactoryExecutionItem.objects.create(execution=execution, alias='AUTO_REMAINING', cleanup_status=3)
            self.assertFalse(DatasourceInfrastructureService.review_ready(self.detail))
            item.cleanup_status = 1
            item.save(update_fields=['cleanup_status'])
            self.assertTrue(DatasourceInfrastructureService.review_ready(self.detail))
