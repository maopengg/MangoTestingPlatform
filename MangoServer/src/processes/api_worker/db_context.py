import threading
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.utils import timezone

from src.apps.test_center.services.database_connection import (
    DatabaseConnection,
    DatabaseConnectionFactory,
)


@dataclass
class _CachedResource:
    value: object
    last_used_at: object
    connection_id: int
    connection_version: object


class WorkerDbContext:
    def __init__(self, idle_seconds: int = 1800):
        self.idle_seconds = idle_seconds
        self.api_connections: dict[str, _CachedResource] = {}
        self.data_factory_engines: dict[str, _CachedResource] = {}

    def invalidate_changed_connection(self, database):
        for resources, closer in (
                (self.api_connections, self._close_api_connection),
                (self.data_factory_engines, self._dispose_engine),
        ):
            for key, resource in list(resources.items()):
                if resource.connection_id == database.id and resource.connection_version != database.update_time:
                    closer(resource.value)
                    resources.pop(key, None)

    def get_api_connection(
            self,
            database: Any,
            test_object: Any | None = None,
            allow_query: bool | None = None,
            allow_write: bool | None = None,
    ) -> DatabaseConnection:
        permission_key = f'{int(bool(allow_query))}:{int(bool(allow_write))}'
        self.invalidate_changed_connection(database)
        key = f'{database.cache_key}:{permission_key}'
        cached = self.api_connections.get(key)
        if cached:
            cached.last_used_at = timezone.now()
            return cached.value
        connection = DatabaseConnectionFactory.create(
            database,
            test_object,
            allow_query=allow_query,
            allow_write=allow_write,
        )
        self.api_connections[key] = _CachedResource(connection, timezone.now(), database.id, database.update_time)
        return connection

    def get_data_factory_engine(self, database: Any):
        self.invalidate_changed_connection(database)
        cached = self.data_factory_engines.get(database.cache_key)
        if cached:
            cached.last_used_at = timezone.now()
            return cached.value

        from src.apps.data_factory.services.datasource import DataFactoryDatasource
        engine = DataFactoryDatasource.create_engine(database)
        self.data_factory_engines[database.cache_key] = _CachedResource(engine, timezone.now(), database.id,
                                                                        database.update_time)
        return engine

    def close_idle(self):
        cutoff_time = timezone.now() - timedelta(seconds=self.idle_seconds)
        for key, cached in list(self.api_connections.items()):
            if cached.last_used_at < cutoff_time:
                self._close_api_connection(cached.value)
                self.api_connections.pop(key, None)
        for key, cached in list(self.data_factory_engines.items()):
            if cached.last_used_at < cutoff_time:
                self._dispose_engine(cached.value)
                self.data_factory_engines.pop(key, None)

    def close_all(self):
        for cached in list(self.api_connections.values()):
            self._close_api_connection(cached.value)
        self.api_connections = {}
        for cached in list(self.data_factory_engines.values()):
            self._dispose_engine(cached.value)
        self.data_factory_engines = {}

    @staticmethod
    def _close_api_connection(connection):
        close_all = getattr(connection, 'close_all', None)
        if callable(close_all):
            close_all()
        else:
            connection.close()

    @staticmethod
    def _dispose_engine(engine):
        dispose = getattr(engine, 'dispose', None)
        if callable(dispose):
            dispose()


class WorkerDbContextRegistry:
    def __init__(self, idle_seconds: int = 1800):
        self.idle_seconds = idle_seconds
        self._local = threading.local()
        self._contexts: set[WorkerDbContext] = set()
        self._lock = threading.Lock()

    def current(self) -> WorkerDbContext:
        context = getattr(self._local, 'worker_db_context', None)
        if context is None:
            context = WorkerDbContext(idle_seconds=self.idle_seconds)
            self._local.worker_db_context = context
            with self._lock:
                self._contexts.add(context)
        return context

    def close_all(self):
        with self._lock:
            contexts = list(self._contexts)
            self._contexts.clear()
        for context in contexts:
            context.close_all()


_current_context = threading.local()


def set_current_worker_db_context(context: WorkerDbContext | None):
    _current_context.value = context


def get_current_worker_db_context() -> WorkerDbContext | None:
    return getattr(_current_context, 'value', None)
