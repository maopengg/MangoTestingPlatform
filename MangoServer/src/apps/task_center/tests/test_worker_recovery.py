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
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService as Results
from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService as Infrastructure
from src.apps.user.models import User


class ProcessIdentityTests(SimpleTestCase):
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
        with patch('src.apps.data_factory.services.datasource_pool.DatasourcePoolRegistry.close_all') as sql, \
                patch('src.apps.data_factory.services.protocol_pool.ProtocolPoolRegistry.close_all') as protocol:
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
                patch('src.apps.data_factory.services.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.protocol_pool.ProtocolPoolRegistry.close_all'):
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
        self.assertEqual((self.detail.status, self.detail.success, self.detail.fail), (3, 0, 0))
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
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        execution = DataFactoryExecution.objects.create(execution_no='AUTO_EMPTY_EXECUTION',
            project_product_id=self.detail.project_product_id, status=0, cleanup_status=3,
            context={CLEANUP_REPORT_CONTEXT_KEY: {'parent_case_detail_id': self.detail.id, 'parent_attempt': 1}})
        with patch('src.apps.data_factory.services.execution_capacity.DatasourceExecutionCapacityService.'
                   'targets_by_scope', return_value={(self.detail.project_product_id, 0): {}}), \
                patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.policy'):
            self.assertTrue(DatasourceInfrastructureService.review_ready(self.detail))
            item = DataFactoryExecutionItem.objects.create(execution=execution, alias='AUTO_REMAINING', cleanup_status=3)
            self.assertFalse(DatasourceInfrastructureService.review_ready(self.detail))
            item.cleanup_status = 1
            item.save(update_fields=['cleanup_status'])
            self.assertTrue(DatasourceInfrastructureService.review_ready(self.detail))
