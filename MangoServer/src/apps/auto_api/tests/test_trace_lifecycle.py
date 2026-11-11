import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStatus, ApiCaseTraceStepType
from src.apps.auto_api.exceptions import AutoApiError, API_CASE_STEP_DEBUG_BUSY
from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder
from src.apps.auto_api.services.execution_trace.reconciliation import ApiTraceReconciliationService as Reconcile
from src.apps.auto_api.services.test_case.test_case import TestCase as RuntimeCase


class TraceLifecycleTests(SimpleTestCase):
    def setUp(self):
        self.recorder = ApiCaseExecutionTraceRecorder()
        self.trace = SimpleNamespace(id=1, trace_id='AUTO_TRACE', status=3, summary={},
                                     started_at=timezone.now(), finished_at=None, save=Mock())
        self.recorder.trace = self.trace
        self.runtime = RuntimeCase.__new__(RuntimeCase)
        self.runtime.trace_recorder = self.recorder
        self.runtime.api_case = SimpleNamespace(id=3425)
        self.runtime.test_env = 0
        self.runtime.user_id = 4

    def test_initialization_failure_after_trace_creation_is_closed(self):
        with patch('src.apps.auto_api.services.test_case.test_case_parts.lifecycle.ApiCaseExecutionTraceRecorder',
                   return_value=self.recorder), patch.object(self.recorder, 'create_trace', return_value=self.trace), \
                patch('src.apps.auto_api.services.test_case.test_case_parts.lifecycle.APIBaseTestSetup',
                      side_effect=AutoApiError(API_CASE_STEP_DEBUG_BUSY)):
            with self.assertRaises(AutoApiError):
                RuntimeCase(user_id=4, test_env=0, case_id=3425)
        self.assertEqual(self.trace.status, ApiCaseTraceStatus.FAIL)
        self.assertIsNotNone(self.trace.finished_at)
        self.assertFalse(self.trace.summary['review_required'])

    def test_invalid_debug_context_and_busy_lock_close_trace_before_any_step(self):
        path = 'src.apps.auto_api.services.test_case.test_case_parts.execution.'
        for context_error in (True, False):
            self.trace.finished_at = None
            with patch(path + 'ApiCaseStepDebugContextService.prepare',
                       side_effect=AutoApiError(API_CASE_STEP_DEBUG_BUSY) if context_error else None), \
                    patch(path + 'acquire_mysql_lock', return_value=False), \
                    patch(path + 'release_mysql_lock') as release:
                with self.assertRaises(AutoApiError):
                    self.runtime.debug_step(7)
            self.assertIsNotNone(self.trace.finished_at)
            release.assert_not_called()

    def test_actual_execution_cancellation_marks_review_and_releases_debug_lock(self):
        path = 'src.apps.auto_api.services.test_case.test_case_parts.execution.'
        with patch(path + 'ApiCaseStepDebugContextService.prepare'), \
                patch(path + 'acquire_mysql_lock', return_value=True), \
                patch(path + 'release_mysql_lock') as release, \
                patch.object(self.runtime, '_debug_step_with_state', side_effect=asyncio.CancelledError()):
            with self.assertRaises(asyncio.CancelledError):
                self.runtime.debug_step(7)
        self.assertTrue(self.trace.summary['review_required'])
        self.assertIsNotNone(self.trace.finished_at)
        release.assert_called_once()

    def test_execution_and_result_write_errors_preserve_exception_without_exposing_it(self):
        error = RuntimeError('private database detail')
        with patch.object(self.runtime, '_test_case', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                self.runtime.test_case()
        self.assertIs(caught.exception, error)
        self.assertNotIn('private database detail', self.trace.error_message)
        self.assertTrue(self.trace.summary['review_required'])
        self.recorder.finish_trace({'status': 1})
        with self.assertRaises(RuntimeError), self.recorder.guard(ApiCaseTraceStepType.REPORT_WRITE.value):
            raise error
        self.assertEqual(self.trace.status, ApiCaseTraceStatus.FAIL)
        self.assertEqual(self.trace.summary['interrupted_stage'], 'report_write')

    def test_normal_return_or_client_disconnect_does_not_abort_live_execution(self):
        with patch.object(self.runtime, '_test_case', return_value='AUTO_RESULT'):
            self.assertEqual(self.runtime.test_case(), 'AUTO_RESULT')
        self.assertIsNone(self.trace.finished_at)
        self.recorder.finish_trace({'status': 1})
        self.assertEqual(self.trace.status, ApiCaseTraceStatus.SUCCESS)

    def test_cancelled_client_wait_does_not_close_sync_execution_still_running(self):
        started, release = threading.Event(), threading.Event()
        def execute(*args, **kwargs):
            started.set()
            release.wait(5)
            self.recorder.finish_trace({'status': 1})
            return 'AUTO_RESULT'
        async def client(pool):
            future = asyncio.get_running_loop().run_in_executor(pool, self.runtime.test_case)
            self.assertTrue(await asyncio.wait_for(asyncio.to_thread(started.wait, 2), timeout=3))
            future.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await future
            self.assertIsNone(self.trace.finished_at)
            release.set()
        with patch.object(self.runtime, '_test_case', side_effect=execute), ThreadPoolExecutor(max_workers=1) as pool:
            asyncio.run(client(pool))
        self.assertIsNotNone(self.trace.finished_at)
        self.assertEqual(self.trace.status, ApiCaseTraceStatus.SUCCESS)


class TraceReconciliationTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.trace = SimpleNamespace(id=1, trace_id='AUTO_TRACE', case_id=3425, user_id=4, test_env=0,
            started_at=self.now-timedelta(hours=1), update_time=self.now-timedelta(hours=1),
            worker_name='example-worker', summary={'execution_owner': {'process_token': 'AUTO_OWNER'}})
        self.query = MagicMock()
        self.query.filter.return_value.order_by.return_value.__getitem__.return_value = [self.trace]
        self.query.filter.return_value.update.return_value = 1
        self.enterContext(patch('src.apps.auto_api.services.execution_trace.reconciliation.ApiQuerySelector.api_case_execution_trace',
                                return_value=self.query))
        self.heartbeats = self.enterContext(patch('src.apps.auto_api.services.execution_trace.reconciliation.ServiceHeartbeatService.get_online_instances',
                                                return_value=[]))
        self.result = self.enterContext(patch('src.apps.auto_api.services.execution_trace.reconciliation.ExecutionResultAccessSelector.exact_api_trace_result',
                                             return_value=None))
        self.completed = self.enterContext(patch('src.apps.auto_api.services.execution_trace.reconciliation.ServiceHeartbeatService.completed_mcp_process',
                                                return_value=False))
        self.steps = self.enterContext(patch('src.apps.auto_api.services.execution_trace.recorder.ApiCaseExecutionTraceRecorder.interrupt_open_steps'))

    def test_drained_owner_closes_interrupted_trace_not_business_success(self):
        self.completed.return_value = True
        self.heartbeats.return_value = [SimpleNamespace(instance_name='example-worker',
            metadata={'process_token': 'AUTO_OWNER'})]
        self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 1)
        changes = self.query.filter.return_value.update.call_args.kwargs
        self.assertEqual(changes['status'], 0)
        self.assertTrue(changes['summary']['review_required'])
        self.steps.assert_called_once()

    def test_fresh_owner_is_never_stopped_due_to_trace_age(self):
        self.heartbeats.return_value = [SimpleNamespace(instance_name='example-worker', metadata={'process_token': 'AUTO_OWNER'})]
        self.assertEqual(Reconcile.reconcile()['trace_active'], 1)
        self.query.filter.return_value.update.assert_not_called()

    def test_missing_heartbeat_is_review_only_not_guessed_terminal(self):
        self.assertEqual(Reconcile.reconcile()['trace_review_required'], 1)
        changes = self.query.filter.return_value.update.call_args.kwargs
        self.assertNotIn('status', changes)
        self.assertNotIn('finished_at', changes)

    def test_only_exact_finalized_result_can_restore_terminal_trace(self):
        for trace_id, finalized, blocked, expected in (
            ('AUTO_OTHER', True, False, False), ('AUTO_TRACE', False, False, False),
            ('AUTO_TRACE', True, True, False), ('AUTO_TRACE', True, False, True),
        ):
            self.result.return_value = SimpleNamespace(id=2, status=1, error_message=None,
                result_data={'trace_id': trace_id, 'status': 1, 'execution_finalized': finalized,
                             'infrastructure_blocked': blocked})
            self.assertEqual(bool(Reconcile.reconcile()['trace_reconciled']), expected)
        changes = self.query.filter.return_value.update.call_args.kwargs
        self.assertEqual(changes['status'], 1)

    def test_final_result_is_reconciled_even_when_its_process_is_still_healthy(self):
        self.heartbeats.return_value = [SimpleNamespace(instance_name='example-worker', metadata={'process_token': 'AUTO_OWNER'})]
        self.result.return_value = SimpleNamespace(id=2, status=1, error_message=None,
            result_data={'trace_id': 'AUTO_TRACE', 'status': 1, 'execution_finalized': True,
                         'infrastructure_blocked': False})
        self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 1)

    def test_file_backed_final_result_requires_verified_contents(self):
        from src.apps.test_center.services.execution_result import ExecutionResultService
        payload = {'trace_id': 'AUTO_TRACE', 'status': 1, 'execution_finalized': True,
                   'infrastructure_blocked': False}
        checksum = ExecutionResultService.calc_result_checksum(payload)
        self.result.return_value = SimpleNamespace(id=2, status=1, error_message=None,
                                                   result_data=None, result_checksum=checksum)
        with patch.object(ExecutionResultService, 'load_result_data', return_value=payload):
            self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 1)
        for stored in (None, {**payload, 'trace_id': 'AUTO_OTHER'}, {**payload, 'status': 0}):
            with self.subTest(stored=stored), patch.object(ExecutionResultService, 'load_result_data', return_value=stored):
                self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 0)
        self.result.return_value.result_checksum = None
        with patch.object(ExecutionResultService, 'load_result_data', return_value=payload):
            self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 0)

    def test_replacement_is_interruption_not_business_pass_and_late_updates_are_fenced(self):
        self.heartbeats.return_value = [SimpleNamespace(instance_name='example-worker', metadata={'process_token': 'AUTO_NEW'},
                                                      last_seen_at=self.now, status=1)]
        with patch('src.apps.auto_api.services.execution_trace.reconciliation.ApiWorkerRecoveryService.replacement_confirmed', return_value=True):
            self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 1)
        changes = self.query.filter.return_value.update.call_args.kwargs
        self.assertEqual(changes['status'], 0)
        self.assertTrue(changes['summary']['review_required'])
        self.query.filter.assert_called_with(id=1, trace_id='AUTO_TRACE', update_time=self.trace.update_time, finished_at__isnull=True)
        self.query.filter.return_value.update.return_value = 0
        self.assertEqual(Reconcile.reconcile()['trace_reconciled'], 0)
