import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone

from src.apps.system.enums import ClientTypeEnum


@dataclass(frozen=True)
class LocalConnection:
    connection_id: str
    user_id: int
    username: str
    client_type: int
    consumer: Any


class LocalConnectionRegistry:
    def __init__(self):
        self._connections_by_id: dict[str, LocalConnection] = {}
        self._actuator_by_user: dict[int, str] = {}
        self._web_by_user: dict[int, set[str]] = {}
        self._dirty_last_seen: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def register(self, connection: LocalConnection) -> LocalConnection | None:
        replaced = None
        async with self._lock:
            self._connections_by_id[connection.connection_id] = connection
            self._dirty_last_seen[connection.connection_id] = timezone.now()
            if connection.client_type == ClientTypeEnum.ACTUATOR.value:
                previous_id = self._actuator_by_user.get(connection.user_id)
                self._actuator_by_user[connection.user_id] = connection.connection_id
                if previous_id and previous_id != connection.connection_id:
                    replaced = self._connections_by_id.pop(previous_id, None)
                    self._dirty_last_seen.pop(previous_id, None)
            elif connection.client_type == ClientTypeEnum.WEB.value:
                self._web_by_user.setdefault(connection.user_id, set()).add(connection.connection_id)
        return replaced

    async def unregister(self, connection_id: str) -> LocalConnection | None:
        async with self._lock:
            connection = self._connections_by_id.pop(connection_id, None)
            self._dirty_last_seen.pop(connection_id, None)
            if connection is None:
                return None
            if connection.client_type == ClientTypeEnum.ACTUATOR.value:
                if self._actuator_by_user.get(connection.user_id) == connection_id:
                    self._actuator_by_user.pop(connection.user_id, None)
            elif connection.client_type == ClientTypeEnum.WEB.value:
                connection_ids = self._web_by_user.get(connection.user_id)
                if connection_ids is not None:
                    connection_ids.discard(connection_id)
                    if not connection_ids:
                        self._web_by_user.pop(connection.user_id, None)
            return connection

    async def touch(self, connection_id: str) -> bool:
        async with self._lock:
            if connection_id not in self._connections_by_id:
                return False
            self._dirty_last_seen[connection_id] = timezone.now()
            return True

    async def drain_dirty_last_seen(self) -> dict[str, datetime]:
        async with self._lock:
            now = timezone.now()
            for connection_id in self._connections_by_id:
                self._dirty_last_seen.setdefault(connection_id, now)
            dirty = self._dirty_last_seen
            self._dirty_last_seen = {}
            return dirty

    async def get_actuator(self, user_id: int) -> LocalConnection | None:
        async with self._lock:
            connection_id = self._actuator_by_user.get(user_id)
            return self._connections_by_id.get(connection_id) if connection_id else None

    async def get_web_connections(self, user_id: int) -> list[LocalConnection]:
        async with self._lock:
            return [
                self._connections_by_id[connection_id]
                for connection_id in self._web_by_user.get(user_id, set())
                if connection_id in self._connections_by_id
            ]

    async def get_all_web_connections(self) -> list[LocalConnection]:
        async with self._lock:
            return [
                connection
                for connection in self._connections_by_id.values()
                if connection.client_type == ClientTypeEnum.WEB.value
            ]

    async def close_all(self, code: int = 1012) -> None:
        async with self._lock:
            connections = list(self._connections_by_id.values())
            self._connections_by_id.clear()
            self._actuator_by_user.clear()
            self._web_by_user.clear()
            self._dirty_last_seen.clear()
        await asyncio.gather(
            *(connection.consumer.close(code=code) for connection in connections),
            return_exceptions=True,
        )

    async def counts(self) -> dict[str, int]:
        async with self._lock:
            return {
                "connections": len(self._connections_by_id),
                "actuators": len(self._actuator_by_user),
                "web": sum(len(value) for value in self._web_by_user.values()),
            }
