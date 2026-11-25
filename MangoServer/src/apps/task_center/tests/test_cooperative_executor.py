import threading
import time
from contextvars import ContextVar
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.task_center.services.execution.cooperative_executor import (
    CooperativeCaseExecutor, wait_until,
)


class CooperativeExecutorTests(SimpleTestCase):
    def setUp(self):
        self.executor = CooperativeCaseExecutor(1, 'cleanup-test')
        self.addCleanup(self.executor.shutdown)
        guard = patch('django.db.connections.all', return_value=[])
        guard.start()
        self.addCleanup(guard.stop)

    def test_wait_resumes_on_same_thread_without_replaying_case(self):
        ready, entered = threading.Event(), threading.Event()
        calls = []
        context = ContextVar('case-test', default=None)

        def case():
            context.set('first')
            calls.append(threading.get_ident())
            entered.set()
            self.assertTrue(wait_until(ready.is_set, 2, interval=0.01))
            self.assertEqual(context.get(), 'first')
            return threading.get_ident()

        first = self.executor.submit(case)
        self.assertTrue(entered.wait(1))

        def other():
            self.assertIsNone(context.get())
            ready.set()
            return 'second'

        second = self.executor.submit(other)
        ready.set()
        self.assertEqual(first.result(timeout=2), calls[0])
        self.assertEqual(second.result(timeout=2), 'second')
        self.assertEqual(len(calls), 1)

    def test_queued_synchronous_case_cannot_delay_ready_cleanup_case(self):
        entered, ready = threading.Event(), threading.Event()
        order = []

        def waiting_case():
            entered.set()
            self.assertTrue(wait_until(ready.is_set, 1, interval=0.005))
            order.append('resumed')

        def long_case():
            order.append('long_started')
            time.sleep(0.15)

        first = self.executor.submit(waiting_case)
        self.assertTrue(entered.wait(1))
        second = self.executor.submit(long_case)
        timer = threading.Timer(0.02, ready.set)
        timer.start()
        self.addCleanup(timer.join)
        first.result(timeout=1)
        second.result(timeout=1)
        self.assertEqual(order, ['resumed', 'long_started'])

    def test_two_workers_keep_ten_slots_and_do_not_multiplex_waiting_cases(self):
        executors = [CooperativeCaseExecutor(5, f'capacity-{i}') for i in range(2)]
        release = threading.Event()
        lock = threading.Lock()
        entered = threading.Event()
        counts = {'active': 0, 'peak': 0, 'started': 0}

        def case():
            with lock:
                counts['active'] += 1
                counts['started'] += 1
                counts['peak'] = max(counts['active'], counts['peak'])
                if counts['active'] == 10:
                    entered.set()
            try:
                self.assertTrue(wait_until(release.is_set, 2, interval=0.005))
            finally:
                with lock:
                    counts['active'] -= 1

        try:
            futures = [executor.submit(case) for executor in executors for _ in range(10)]
            self.assertTrue(entered.wait(1))
            time.sleep(0.03)
            with lock:
                self.assertEqual(counts['started'], 10)
            release.set()
            for future in futures:
                future.result(timeout=2)
            self.assertEqual(counts['started'], 20)
            self.assertEqual(counts['peak'], 10)
        finally:
            release.set()
            for executor in executors:
                executor.shutdown()

    def test_timeout_does_not_become_success(self):
        result = self.executor.submit(lambda: wait_until(lambda: False, 0.01, interval=0.005))
        self.assertFalse(result.result(timeout=1))

    def test_ready_failure_is_delivered_to_original_case(self):
        calls = []

        def ready():
            calls.append(1)
            if len(calls) > 1:
                raise RuntimeError('verification unavailable')
            return False

        result = self.executor.submit(lambda: wait_until(ready, 1, interval=0.01))
        with self.assertRaisesRegex(RuntimeError, 'verification unavailable'):
            result.result(timeout=1)
