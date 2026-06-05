import threading
from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.utils import timezone

from src.services.runtime.api_worker.db_context import WorkerDbContext, WorkerDbContextRegistry


class _FakeConnection:
    def __init__(self):
        self.closed = False

    def close_all(self):
        self.closed = True


class _FakeEngine:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class WorkerDbContextTests(TestCase):
    def test_api_connection_reused_in_same_context(self):
        database = SimpleNamespace(id=1)
        test_object = SimpleNamespace(id=2)
        connection = _FakeConnection()

        with patch(
                'src.services.runtime.api_worker.db_context.DatabaseConnectionFactory.create',
                return_value=connection,
        ) as create:
            context = WorkerDbContext()
            first = context.get_api_connection(database, test_object)
            second = context.get_api_connection(database, test_object)

        self.assertIs(first, second)
        self.assertEqual(create.call_count, 1)

    def test_registry_keeps_context_thread_local(self):
        registry = WorkerDbContextRegistry()
        main_context = registry.current()
        worker_context_list = []

        thread = threading.Thread(target=lambda: worker_context_list.append(registry.current()))
        thread.start()
        thread.join()

        self.assertIsNot(main_context, worker_context_list[0])

    def test_idle_resources_are_closed(self):
        context = WorkerDbContext(idle_seconds=1800)
        connection = _FakeConnection()
        engine = _FakeEngine()
        context.api_connections['1:1'] = SimpleNamespace(
            value=connection,
            last_used_at=timezone.now() - timedelta(seconds=1801),
        )
        context.data_factory_engines[1] = SimpleNamespace(
            value=engine,
            last_used_at=timezone.now() - timedelta(seconds=1801),
        )

        context.close_idle()

        self.assertTrue(connection.closed)
        self.assertTrue(engine.disposed)
        self.assertFalse(context.api_connections)
        self.assertFalse(context.data_factory_engines)

    def test_registry_close_all_closes_contexts(self):
        registry = WorkerDbContextRegistry()
        context = registry.current()
        connection = _FakeConnection()
        context.api_connections['1:1'] = SimpleNamespace(value=connection, last_used_at=timezone.now())

        registry.close_all()

        self.assertTrue(connection.closed)
