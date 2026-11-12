import threading
import time
import logging
from contextvars import Context
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import create_engine, text

from src.apps.data_factory.services.pool.datasource_pool import DatasourceQueuePool
from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService as Waiting
from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor
from src.apps.task_center.services.execution.claim import ApiTaskClaimService


class DatasourceWaitTests(SimpleTestCase):
    def setUp(self):
        logger = logging.getLogger('src.apps.data_factory.services.pool.datasource_pool.DatasourceQueuePool')
        previous_level = logger.level
        logger.setLevel(logging.WARNING)
        self.addCleanup(logger.setLevel, previous_level)

    def engine(self, size=2, **kwargs):
        engine = create_engine('sqlite://', poolclass=DatasourceQueuePool, pool_size=size,
                               max_overflow=0, pool_timeout=0,
                               connect_args={'check_same_thread': False}, **kwargs)
        self.addCleanup(engine.dispose)
        return engine

    def wait_queue(self, pool, count):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            with pool._admission_lock:
                if len(pool._admission_queue) == count:
                    return
            time.sleep(0.005)
        self.fail(f'Expected {count} pool waiters')

    def test_borrowed_connections_cannot_park_cases_while_waiting_for_sql_admission(self):
        engine = self.engine()
        executor = CooperativeCaseExecutor(2, 'AUTO_CONNECTION_HOLD')

        def case():
            with Waiting.owner(lambda: None):
                with engine.connect() as connection:
                    self.assertTrue(Waiting.connection_held())
                    Waiting.pause(1)
                    return connection.execute(text('select 1')).scalar_one()

        with patch('django.db.connections.all', return_value=[]):
            futures = [executor.submit(case) for _ in range(2)]
            try:
                self.assertEqual([future.result(timeout=3) for future in futures], [1, 1])
            finally:
                executor.shutdown()
        self.assertEqual(engine.pool.checkedout(), 0)

    def test_connection_creation_keeps_execution_slot_before_checkout_event(self):
        import sqlite3
        def creator():
            self.assertTrue(Waiting.connection_held())
            Waiting.pause(1)
            return sqlite3.connect(':memory:', check_same_thread=False)
        engine = self.engine(creator=creator)
        executor = CooperativeCaseExecutor(1, 'AUTO_CONNECTION_CREATE')
        def case():
            with Waiting.owner(lambda: None):
                with engine.connect():
                    self.assertTrue(Waiting.connection_held())
            self.assertFalse(Waiting.connection_held())
        with patch('django.db.connections.all', return_value=[]):
            future = executor.submit(case)
            try:
                future.result(timeout=3)
            finally:
                executor.shutdown()

    def test_connection_hold_clears_on_rollback_invalidation_and_pool_recreation(self):
        engine = self.engine()
        with self.assertRaisesRegex(RuntimeError, 'AUTO_ROLLBACK'):
            with engine.begin() as connection:
                self.assertTrue(Waiting.connection_held())
                connection.execute(text('select 1'))
                raise RuntimeError('AUTO_ROLLBACK')
        self.assertFalse(Waiting.connection_held())
        with engine.connect() as connection:
            connection.invalidate()
            self.assertFalse(Waiting.connection_held())
        engine.dispose()
        with engine.connect():
            self.assertTrue(Waiting.connection_held())
        self.assertFalse(Waiting.connection_held())
        self.assertEqual(engine.pool.checkedout(), 0)

    def test_nested_borrow_and_checkin_in_another_context_do_not_leave_stale_holds(self):
        engine = self.engine()
        first, second = engine.connect(), engine.connect()
        try:
            Context().run(first.close)
            self.assertTrue(Waiting.connection_held())
            second.close()
            self.assertFalse(Waiting.connection_held())
        finally:
            first.close()
            second.close()

    def test_pool_waiters_are_fifo_under_thread_contention(self):
        engine = self.engine(size=1)
        held = engine.connect()
        jobs, order, errors = [], [], []
        def borrow(index):
            try:
                with engine.connect() as connection:
                    order.append(index)
                    self.assertEqual(connection.execute(text('select 1')).scalar_one(), 1)
            except BaseException as error:
                errors.append(error)
        try:
            for index in range(12):
                job = threading.Thread(target=borrow, args=(index,))
                job.start()
                jobs.append(job)
                self.wait_queue(engine.pool, index + 1)
        finally:
            held.close()
            for job in jobs:
                job.join(timeout=5)
        self.assertFalse(errors)
        self.assertTrue(all(not job.is_alive() for job in jobs))
        self.assertEqual(order, list(range(12)))
        self.assertEqual(engine.pool.checkedout(), 0)

    def test_slow_connection_creation_does_not_block_reuse_of_returned_connection(self):
        import sqlite3
        creating, finish, reused = threading.Event(), threading.Event(), threading.Event()
        errors, calls = [], []
        def creator():
            calls.append(1)
            if len(calls) == 2:
                creating.set()
                if not finish.wait(3):
                    raise AssertionError('AUTO_CONNECT_NOT_RELEASED')
            return sqlite3.connect(':memory:', check_same_thread=False)
        engine = self.engine(creator=creator)
        held = engine.connect()
        def borrow(signal=None):
            try:
                with engine.connect() as connection:
                    self.assertEqual(connection.execute(text('select 1')).scalar_one(), 1)
                    if signal is not None:
                        signal.set()
            except BaseException as error:
                errors.append(error)
        slow = threading.Thread(target=borrow)
        quick = threading.Thread(target=borrow, args=(reused,))
        slow.start()
        try:
            self.assertTrue(creating.wait(1))
            held.close()
            quick.start()
            self.assertTrue(reused.wait(1))
            self.assertTrue(slow.is_alive())
        finally:
            held.close()
            finish.set()
            slow.join(timeout=3)
            if quick.ident is not None:
                quick.join(timeout=3)
        self.assertFalse(errors)
        self.assertEqual(len(calls), 2)
        self.assertEqual(engine.pool.checkedout(), 0)

    def test_connection_wait_keeps_case_capacity_without_a_second_admission(self):
        from src.apps.task_center.services.execution import cooperative_executor
        self.assertFalse(hasattr(cooperative_executor, 'resource_parking'))
        self.assertFalse(hasattr(cooperative_executor, 'parked_resource_wait'))
        executor = CooperativeCaseExecutor(1, 'AUTO_FREE_WAIT')
        def case():
            with Waiting.owner(lambda: None):
                Waiting.pause(1, ready=lambda: True)
        with patch('django.db.connections.all', return_value=[]):
            try:
                executor.submit(case).result(timeout=3)
            finally:
                executor.shutdown()

    def test_cancelled_head_waiter_does_not_block_following_case(self):
        engine = self.engine(size=1)
        held = engine.connect()
        cancel, failures, completed = threading.Event(), [], []
        def cancelled():
            def pulse():
                if cancel.is_set():
                    raise RuntimeError('AUTO_OWNER_CHANGED')
            try:
                with Waiting.owner(pulse), engine.connect():
                    self.fail('Cancelled Case must not execute SQL')
            except RuntimeError as error:
                failures.append(str(error))
        def following():
            with engine.connect() as connection:
                completed.append(connection.execute(text('select 2')).scalar_one())
        first, second = threading.Thread(target=cancelled), threading.Thread(target=following)
        first.start()
        try:
            self.wait_queue(engine.pool, 1)
            second.start()
            self.wait_queue(engine.pool, 2)
            cancel.set()
            first.join(timeout=2)
            self.assertFalse(first.is_alive())
            self.wait_queue(engine.pool, 1)
        finally:
            cancel.set()
            held.close()
            first.join(timeout=3)
            if second.ident is not None:
                second.join(timeout=3)
        self.assertEqual(failures, ['AUTO_OWNER_CHANGED'])
        self.assertEqual(completed, [2])

    def test_driver_connection_timeout_is_not_retried_and_releases_hold_and_ticket(self):
        from sqlalchemy.exc import TimeoutError
        creator = Mock(side_effect=TimeoutError('AUTO_CONNECT_TIMEOUT', code='driver_timeout'))
        engine = self.engine(creator=creator)
        with self.assertRaises(TimeoutError):
            engine.connect()
        creator.assert_called_once()
        self.assertFalse(Waiting.connection_held())
        self.assertEqual(len(engine.pool._admission_queue), 0)

    def test_high_concurrency_cooperative_cases_return_all_connections_without_replay(self):
        engine = self.engine()
        executor = CooperativeCaseExecutor(2, 'AUTO_CONCURRENT_POOL')
        executed = []
        def case(index):
            with Waiting.owner(lambda: None), engine.begin() as connection:
                Waiting.pause(0.01)
                executed.append(index)
                return connection.execute(text('select 1')).scalar_one()
        with patch('django.db.connections.all', return_value=[]):
            try:
                futures = [executor.submit(case, index) for index in range(30)]
                self.assertEqual([future.result(timeout=10) for future in futures], [1] * 30)
            finally:
                executor.shutdown()
        self.assertEqual(sorted(executed), list(range(30)))
        self.assertEqual(engine.pool.checkedout(), 0)
        self.assertEqual(len(engine.pool._admission_queue), 0)

    def test_pool_return_signals_head_waiter(self):
        engine = self.engine(size=1)
        held = engine.connect()
        ticket = threading.Event()
        with engine.pool._admission_lock:
            engine.pool._admission_queue.append(ticket)
        try:
            held.close()
            self.assertTrue(ticket.is_set())
        finally:
            with engine.pool._admission_lock:
                engine.pool._admission_queue.remove(ticket)

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
        with Waiting.owner(pulse):
            Waiting.pause(0.001)
            self.assertGreater(Waiting.elapsed(), 0)
        pulse.assert_called_once()

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
