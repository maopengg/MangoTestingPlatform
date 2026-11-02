from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from src.apps.system.enums import ClientNameEnum
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import SocketConnectionStatusEnum
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.exceptions import (
    SYSTEM_TASK_SEND_FAILED,
    SystemError,
)
from src.apps.task_center.models import SocketConnection
from src.apps.user.models import User


@dataclass(frozen=True)
class SocketConnectionRegistration:
    connection: SocketConnection
    replaced_connection_ids: tuple[str, ...]


class SocketConnectionService:
    ONLINE_TIMEOUT_SECONDS = 60
    DRAINING_TTL_SECONDS = 10 * 60
    CAPABILITY_TTL_SECONDS = 90

    @classmethod
    @transaction.atomic
    def register(
            cls,
            *,
            user_id: int,
            client_type: int,
            channel_name: str,
            service_instance: str,
    ) -> SocketConnectionRegistration:
        user = User.objects.select_for_update().get(id=user_id)
        now = timezone.now()
        replaced_ids: list[str] = []
        if client_type == ClientTypeEnum.ACTUATOR.value:
            existing = list(
                SocketConnection.objects.select_for_update().filter(
                    user=user,
                    client_type=client_type,
                    status=SocketConnectionStatusEnum.ONLINE.value,
                )
            )
            replaced_ids = [str(item.connection_id) for item in existing]
            if existing:
                SocketConnection.objects.filter(id__in=[item.id for item in existing]).update(
                    status=SocketConnectionStatusEnum.OFFLINE.value,
                    disconnected_at=now,
                    update_time=now,
                )
        connection = SocketConnection.objects.create(
            user=user,
            client_type=client_type,
            channel_name=channel_name,
            service_instance=service_instance,
            status=SocketConnectionStatusEnum.ONLINE.value,
            connected_at=now,
            last_seen_at=now,
        )
        return SocketConnectionRegistration(connection, tuple(replaced_ids))

    @staticmethod
    def touch(connection_id: str | UUID) -> bool:
        now = timezone.now()
        return bool(
            SocketConnection.objects.filter(
                connection_id=connection_id,
                status=SocketConnectionStatusEnum.ONLINE.value,
            ).update(last_seen_at=now, update_time=now)
        )

    @staticmethod
    def bulk_touch(last_seen_by_connection: dict[str, object]) -> int:
        if not last_seen_by_connection:
            return 0
        connections = list(
            SocketConnection.objects.filter(
                connection_id__in=last_seen_by_connection,
                status=SocketConnectionStatusEnum.ONLINE.value,
            )
        )
        for connection in connections:
            connection.last_seen_at = last_seen_by_connection[str(connection.connection_id)]
            connection.update_time = connection.last_seen_at
        if connections:
            SocketConnection.objects.bulk_update(connections, ["last_seen_at", "update_time"])
        return len(connections)

    @staticmethod
    def disconnect(connection_id: str | UUID) -> bool:
        now = timezone.now()
        return bool(
            SocketConnection.objects.filter(
                connection_id=connection_id,
                status=SocketConnectionStatusEnum.ONLINE.value,
            ).update(
                status=SocketConnectionStatusEnum.OFFLINE.value,
                disconnected_at=now,
                update_time=now,
            )
        )

    @staticmethod
    def get_current_actuator(user_id: int) -> SocketConnection | None:
        return (
            SocketConnection.objects.filter(
                user_id=user_id,
                client_type=ClientTypeEnum.ACTUATOR.value,
                status=SocketConnectionStatusEnum.ONLINE.value,
            )
            .order_by("-last_seen_at", "-id")
            .first()
        )

    @classmethod
    def is_actuator_online(cls, user_id: int, timeout_seconds: int = 60) -> bool:
        connection = cls.get_current_actuator(user_id)
        if connection is None:
            return False
        return connection.last_seen_at >= timezone.now() - timedelta(seconds=timeout_seconds)

    @classmethod
    def require_actuator(cls, username: str, timeout_seconds: int | None = None) -> SocketConnection:
        timeout = timeout_seconds or cls.ONLINE_TIMEOUT_SECONDS
        connection = (
            SocketConnection.objects.select_related("user")
            .filter(
                user__username=username,
                client_type=ClientTypeEnum.ACTUATOR.value,
                status=SocketConnectionStatusEnum.ONLINE.value,
                last_seen_at__gte=timezone.now() - timedelta(seconds=timeout),
            )
            .order_by("-last_seen_at", "-id")
            .first()
        )
        if connection is None:
            raise SystemError(SYSTEM_TASK_SEND_FAILED,
                              value=(ClientNameEnum.DRIVER.value, ClientNameEnum.SERVER.value),
                              )
        return connection

    @classmethod
    def list_online_actuators(cls, timeout_seconds: int | None = None) -> list[SocketConnection]:
        timeout = timeout_seconds or cls.ONLINE_TIMEOUT_SECONDS
        return list(
            SocketConnection.objects.select_related("user")
            .filter(
                client_type=ClientTypeEnum.ACTUATOR.value,
                status=SocketConnectionStatusEnum.ONLINE.value,
                last_seen_at__gte=timezone.now() - timedelta(seconds=timeout),
            )
            .order_by("user_id", "-last_seen_at", "-id")
        )

    @classmethod
    def list_open_actuator_usernames(cls) -> list[str]:
        return [
            connection.user.username
            for connection in cls.list_online_actuators()
            if connection.is_open and not cls.is_draining(connection.connection_id)
        ]

    @classmethod
    def update_capabilities(
            cls,
            connection_id: str | UUID,
            supported_task_types: list[str],
            protocol_versions: dict[str, int],
            capability_capacities: dict[str, int] | None = None,
    ) -> None:
        RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).set(
            cls._capability_key(connection_id),
            {
                "supported_task_types": sorted({str(item) for item in supported_task_types if item}),
                "protocol_versions": {str(key): int(value) for key, value in protocol_versions.items()},
                "capability_capacities": {
                    str(key): max(0, int(value))
                    for key, value in (capability_capacities or {}).items()
                },
            },
            ttl=cls.CAPABILITY_TTL_SECONDS,
        )

    @classmethod
    def supports_task_type(cls, connection_id: str | UUID, task_type: str) -> bool:
        capabilities = RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).get(
            cls._capability_key(connection_id),
        ) or {}
        return str(task_type) in set(capabilities.get("supported_task_types") or [])

    @classmethod
    def capability_capacity(cls, connection_id: str | UUID, capability: str, default: int = 0) -> int:
        capabilities = RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).get(
            cls._capability_key(connection_id),
        ) or {}
        values = capabilities.get("capability_capacities") or {}
        return max(0, int(values.get(str(capability), default) or 0))

    @classmethod
    def set_draining(cls, connection_id: str | UUID, draining: bool) -> None:
        key = cls._draining_key(connection_id)
        if draining:
            RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).set(key, True, ttl=cls.DRAINING_TTL_SECONDS)
        else:
            RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).delete(key)

    @classmethod
    def is_draining(cls, connection_id: str | UUID) -> bool:
        return bool(RuntimeKV.namespace(RuntimeKVNamespaceEnum.EXECUTOR_STATE).get(cls._draining_key(connection_id)))

    @staticmethod
    def _draining_key(connection_id: str | UUID) -> str:
        return f"executor-task:draining:{connection_id}"

    @staticmethod
    def _capability_key(connection_id: str | UUID) -> str:
        return f"executor-task:capabilities:{connection_id}"

    @staticmethod
    def update_actuator_runtime(
            user_id: int,
            *,
            is_open: bool | None = None,
            debug: bool | None = None,
            web_live_stream_supported: bool | None = None,
    ) -> SocketConnection | None:
        connection = SocketConnectionService.get_current_actuator(user_id)
        if connection is None:
            return None
        update_fields: list[str] = []
        if is_open is not None:
            connection.is_open = bool(is_open)
            update_fields.append("is_open")
        if debug is not None:
            connection.debug = bool(debug)
            update_fields.append("debug")
        if web_live_stream_supported is not None:
            connection.web_live_stream_supported = bool(web_live_stream_supported)
            update_fields.append("web_live_stream_supported")
        if update_fields:
            update_fields.append("update_time")
            connection.save(update_fields=update_fields)
        return connection

    @staticmethod
    def expire_stale(timeout_seconds: int = 60) -> int:
        now = timezone.now()
        cutoff = now - timedelta(seconds=timeout_seconds)
        return SocketConnection.objects.filter(
            status=SocketConnectionStatusEnum.ONLINE.value,
            last_seen_at__lt=cutoff,
        ).update(
            status=SocketConnectionStatusEnum.OFFLINE.value,
            disconnected_at=now,
            update_time=now,
        )

    @staticmethod
    def disconnect_service(service_instance: str) -> int:
        now = timezone.now()
        return SocketConnection.objects.filter(
            service_instance=service_instance,
            status=SocketConnectionStatusEnum.ONLINE.value,
        ).update(
            status=SocketConnectionStatusEnum.OFFLINE.value,
            disconnected_at=now,
            update_time=now,
        )

    @staticmethod
    def cleanup_history(retention_days: int = 7, batch_size: int = 1000) -> int:
        cutoff = timezone.now() - timedelta(days=retention_days)
        ids = list(
            SocketConnection.objects.filter(
                status=SocketConnectionStatusEnum.OFFLINE.value,
                disconnected_at__lt=cutoff,
            )
            .order_by("id")
            .values_list("id", flat=True)[:batch_size]
        )
        if not ids:
            return 0
        deleted, _ = SocketConnection.objects.filter(id__in=ids).delete()
        return deleted
