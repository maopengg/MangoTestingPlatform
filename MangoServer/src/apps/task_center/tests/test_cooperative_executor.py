import threading
from contextvars import ContextVar
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.task_center.services.execution.cooperative_executor import CooperativeCaseExecutor, wait_until


class CooperativeExecutorTests(SimpleTestCase):
    def setUp(self):
        self.executor = CooperativeCaseExecutor(1, 'cleanup-test')
        self.addCleanup(self.executor.shutdown)
        guard = patch('django.db.connections.all', return_value=[])
        guard.start()
        self.addCleanup(guard.stop)

    def test_wait_yields_without_replaying_case_and_resumes_on_same_thread(self):
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

        self.assertEqual(self.executor.submit(other).result(timeout=2), 'second')
        self.assertEqual(first.result(timeout=2), calls[0])
        self.assertEqual(len(calls), 1)

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
