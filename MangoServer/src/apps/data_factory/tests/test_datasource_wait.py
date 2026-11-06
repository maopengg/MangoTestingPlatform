import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import create_engine, text

from src.apps.data_factory.services.datasource_pool import DatasourceQueuePool
from src.apps.data_factory.services.datasource_wait import DatasourceWaitService as Waiting
from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor
from src.apps.task_center.services.execution.claim import ApiTaskClaimService


class DatasourceWaitTests(SimpleTestCase):
    def setUp(self):
        guard = patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.renew_waiting_operation')
        guard.start()
        self.addCleanup(guard.stop)

    def test_pool_wait_yields_same_thread_and_does_not_replay_sql(self):
        engine = create_engine('sqlite://', poolclass=DatasourceQueuePool, pool_size=1,
                               max_overflow=0, pool_timeout=0, connect_args={'check_same_thread': False})
        executor = CooperativeCaseExecutor(1, 'pool-wait-test')
        self.addCleanup(engine.dispose)
        self.addCleanup(executor.shutdown)
        entered = threading.Event()
        calls = []
        pulse = Mock()

        def first():
            with engine.connect() as connection:
                entered.set()
                with Waiting.owner(pulse):
                    Waiting.pause(0.2)
                calls.append(connection.execute(text('select 1')).scalar_one())

        def second():
            with engine.connect() as connection:
                calls.append(connection.execute(text('select 2')).scalar_one())

        with patch('django.db.connections.all', return_value=[]):
            a = executor.submit(first)
            self.assertTrue(entered.wait(1))
            b = executor.submit(second)
            a.result(timeout=3)
            b.result(timeout=3)
        self.assertEqual(calls, [1, 2])
        pulse.assert_called_once()
        self.assertEqual(engine.pool.checkedout(), 0)

    def test_lost_owner_interrupts_wait_without_dispatching_operation(self):
        operation = Mock()
        with Waiting.owner(Mock(side_effect=RuntimeError('owner changed'))):
            with self.assertRaisesRegex(RuntimeError, 'owner changed'):
                Waiting.pause()
                operation()
        operation.assert_not_called()

    def test_control_lock_wait_checks_owner_without_recursive_quota_renewal(self):
        pulse = Mock()
        with patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.renew_waiting_operation') as renew:
            with Waiting.owner(pulse):
                Waiting.pause(0.001, renew_operation=False)
                self.assertGreater(Waiting.elapsed(), 0)
            pulse.assert_called_once()
            renew.assert_not_called()

    def test_wait_renewal_fences_attempt_expiry_and_stopped_report(self):
        from mangotools.enums import TaskEnum
        from src.apps.task_center.services.execution import claim
        row = Mock()
        row.filter.return_value = row
        row.exclude.return_value.update.return_value = 0
        with patch.object(claim.TestSuiteDetails.objects, 'filter', return_value=row) as query:
            self.assertFalse(ApiTaskClaimService.renew_wait(
                SimpleNamespace(test_suite_details=17, attempt=2), 3600))
        self.assertEqual(query.call_args.kwargs['id'], 17)
        self.assertEqual(query.call_args.kwargs['retry'], 2)
        self.assertEqual(query.call_args.kwargs['status'], TaskEnum.PROCEED.value)
        self.assertIn('push_time__gte', query.call_args.kwargs)
        row.exclude.assert_called_once_with(test_suite__status=TaskEnum.STOPPED.value)
