import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
from src.apps.data_factory.services.datasource_wait import DatasourceWaitService as Waiting
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService as Audit, SqlExecutionAuditHandle
from src.apps.data_factory.services.sql_driver_audit import TimedResultCursor
from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor, cooperative_sleep
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class DatasourceTimingTests(SimpleTestCase):
    def test_nested_measurements_are_exclusive_and_context_restores(self):
        clock = [0]
        with patch('src.apps.data_factory.services.datasource_timing.monotonic', side_effect=lambda: clock[0]):
            with Timing.scope():
                with Timing.measure(Phase.EXECUTE):
                    clock[0] = 1
                    with Timing.measure(Phase.CONNECT):
                        clock[0] = 3
                    clock[0] = 4
                self.assertEqual(Timing.snapshot(), {'connect': 2000, 'execute': 2000})
                with Timing.scope():
                    self.assertEqual(Timing.snapshot(), {})
                self.assertEqual(Timing.snapshot()['execute'], 2000)

    def test_wait_segments_separate_scheduler_delay_without_counting_it_twice(self):
        with Timing.scope(), Timing.waiting(Phase.CONNECTION_SLOT):
            Timing.waited(1.5, 0.4)
            handle = SqlExecutionAuditHandle(SimpleNamespace(source_detail={}), 0, wait_started=0,
                                            timing_started={})
            with patch.object(Waiting, 'elapsed', return_value=1.5):
                self.assertEqual(Audit.measured_duration(handle, 2000), 500)
            self.assertEqual(handle.record.source_detail['timing_ms'],
                             {'connection_slot': 1100, 'scheduler_resume': 400})

    def test_control_renewal_inside_pause_is_not_counted_twice(self):
        clock = [10.0]
        def renew():
            with Waiting.control_io():
                clock[0] += 2
        def wait(*args, **kwargs):
            clock[0] += 1
        with patch('src.apps.data_factory.services.datasource_wait.monotonic', side_effect=lambda: clock[0]), \
                patch('src.apps.data_factory.services.datasource_timing.monotonic', side_effect=lambda: clock[0]), \
                patch.object(Governor, 'renew_waiting_operation', side_effect=renew), \
                patch('src.apps.task_center.services.execution.cooperative_executor.wait_until', side_effect=wait):
            with Waiting.owner(None), Timing.waiting(Phase.LOCAL_POOL):
                Waiting.pause(1)
                self.assertEqual(Waiting.elapsed(), 3)
                self.assertEqual(Timing.snapshot(), {'control_io': 2000, 'local_pool': 1000, 'scheduler_resume': 0})

    def test_long_wait_logs_are_limited_and_do_not_include_operation_or_credentials(self):
        with patch('src.apps.data_factory.services.datasource_timing.monotonic', return_value=31), \
                patch('src.apps.data_factory.services.datasource_timing.log.debug') as log, \
                Audit.source({'case_id': 12, 'source_stage': 'cleanup', 'password': 'AUTO_SECRET',
                              'sql': 'AUTO_PRIVATE_SQL'}):
            next_log = Timing.diagnose(0, 30, phase=Phase.LOCAL_POOL, database_id=1,
                                      wait_kind='capacity', checked_out=3, pool_size=3)
            Timing.diagnose(0, next_log, phase=Phase.LOCAL_POOL, database_id=1)
        log.assert_called_once()
        self.assertIn('case_id', str(log.call_args))
        self.assertIn('capacity', str(log.call_args))
        self.assertIn('checked_out=%s pool_size=%s', log.call_args.args[0])
        self.assertNotIn('AUTO_SECRET', str(log.call_args))
        self.assertNotIn('AUTO_PRIVATE_SQL', str(log.call_args))

    def test_physical_gate_is_not_acquired_before_connection_or_protocol_pool(self):
        with patch.object(Governor, 'acquire') as acquire:
            for kind in (DataSourceTypeEnum.MYSQL, DataSourceTypeEnum.POSTGRESQL,
                         DataSourceTypeEnum.REDIS, DataSourceTypeEnum.ELASTICSEARCH):
                with self.subTest(kind=kind), patch.object(Governor, 'target_policy', return_value=(None, None, 'group')):
                    with Governor._operation(SimpleNamespace(db_type=kind.value)) as admission:
                        self.assertIsNone(admission)
            acquire.assert_not_called()

    def test_fetch_failure_is_timed_and_propagates_unchanged(self):
        error = RuntimeError('AUTO_FETCH_FAILURE')
        cursor = TimedResultCursor(Mock(fetchall=Mock(side_effect=error)))
        with Timing.scope():
            with self.assertRaises(RuntimeError) as raised:
                cursor.fetchall()
            self.assertIn('fetch', Timing.snapshot())
        self.assertIs(raised.exception, error)

    def test_case_sleep_yields_thread_and_timing_is_not_shared_between_cases(self):
        executor = CooperativeCaseExecutor(1, 'timing-isolation')
        self.addCleanup(executor.shutdown)
        entered = threading.Event()

        def waiting():
            with Waiting.owner(None):
                Timing.add(Phase.EXECUTE, 0.5)
                entered.set()
                cooperative_sleep(0.1)
                return Timing.snapshot()

        with patch('django.db.connections.all', return_value=[]):
            first = executor.submit(waiting)
            self.assertTrue(entered.wait(1))
            second = executor.submit(Timing.snapshot)
            self.assertEqual(second.result(timeout=1), {})
            self.assertEqual(first.result(timeout=1), {'execute': 500})

    def test_transaction_does_not_yield_to_another_case(self):
        executor = CooperativeCaseExecutor(1, 'transaction-isolation')
        self.addCleanup(executor.shutdown)
        entered = threading.Event()
        order = []

        def atomic_case():
            entered.set()
            cooperative_sleep(0.03)
            order.append('atomic_finished')

        with patch('django.db.connections.all', return_value=[SimpleNamespace(in_atomic_block=True)]):
            first = executor.submit(atomic_case)
            self.assertTrue(entered.wait(1))
            second = executor.submit(lambda: order.append('other_started'))
            first.result(timeout=1)
            second.result(timeout=1)
        self.assertEqual(order, ['atomic_finished', 'other_started'])

    def test_registry_lock_contention_yields_instead_of_blocking_case_thread(self):
        lock = threading.RLock()
        held, release, waiting = threading.Event(), threading.Event(), threading.Event()
        def holder():
            with lock:
                held.set()
                release.wait(2)
        thread = threading.Thread(target=holder)
        thread.start()
        self.addCleanup(lambda: thread.join(timeout=3))
        self.addCleanup(release.set)
        self.assertTrue(held.wait(1))
        executor = CooperativeCaseExecutor(1, 'registry-lock-wait')
        self.addCleanup(executor.shutdown)
        def borrow():
            with Waiting.owner(None):
                waiting.set()
                with Timing.locked(lock):
                    return Timing.snapshot()
        with patch('django.db.connections.all', return_value=[]), \
                patch.object(Governor, 'renew_waiting_operation'):
            first = executor.submit(borrow)
            self.assertTrue(waiting.wait(1))
            executor.submit(release.set).result(timeout=1)
            self.assertGreater(first.result(timeout=1)['local_pool'], 0)
