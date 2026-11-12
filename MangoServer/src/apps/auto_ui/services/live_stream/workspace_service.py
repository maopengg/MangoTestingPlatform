import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock

import sys
from django.core.cache import cache
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract

from src.apps.auto_ui.enums.live_stream import (
    LiveStreamCommand,
    LiveStreamExecutionType,
)
from src.apps.auto_ui.constants import LIVE_WORKSPACE_RECORD_KEY_PREFIX
from src.apps.auto_ui.exceptions import (
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED,
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED_CODE_TYPE_UNSUPPORTED,
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_REQUIRED,
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED,
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED_CODE_ACCESS_DENIED,
    AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_EXECUTOR_USER_EXECUTION_INVALID,
    AutoUiError,
)
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.live_stream.constants import REALTIME_COMMAND_TTL_SECONDS
from src.apps.auto_ui.services.execution.cases.test_case import TestCase
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.common.logging import log


@dataclass
class LiveWorkspaceRecord:
    workspace_id: str
    workspace_type: str
    resource_id: int
    test_env: int
    username: str
    executor_username: str
    connection_id: str
    user_id: int = 0
    slot_id: str = ""
    idle_deadline: float = 0
    active_user_count: int = 0
    max_user_count: int = ExecutorSlotLeaseService.MAX_USERS
    available_user_count: int = ExecutorSlotLeaseService.MAX_USERS
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    detached_at: datetime | None = None
    runtime_data: dict | None = None
    status: str = "initializing"
    error_message: str = ""


class LiveWorkspaceService:
    """管理 UI 实时工作区，并确保多进程服务读取同一份工作区状态。"""

    _lock = RLock()
    _workspace_by_key: dict[str, LiveWorkspaceRecord] = {}
    _workspace_by_id: dict[str, LiveWorkspaceRecord] = {}
    _keep_alive_seconds = ExecutorSlotLeaseService.IDLE_TIMEOUT_SECONDS
    _cache_ttl_seconds = 24 * 60 * 60

    @classmethod
    def create_workspace(
            cls,
            user: dict,
            workspace_type: str,
            resource_id: int,
            test_env: int,
            actuator_username: str | None = None,
    ) -> dict:
        if workspace_type not in (
                LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
                LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
        ):
            raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED_CODE_TYPE_UNSUPPORTED)
        connection = cls._resolve_executor(user, actuator_username)
        if connection is None:
            actuators = cls.available_actuators(user)
            log.ui.info(
                f"UI实时工作区无直属执行器：user={user['username']}，"
                f"type={workspace_type}，resource={resource_id}，可选执行器={len(actuators)}"
            )
            if actuators:
                return {
                    "status": "select_actuator",
                    "actuators": actuators,
                    "msg": "当前账号执行器不在线，请选择一个已开放的执行器",
                }
            connection = SocketConnectionService.require_actuator(user['username'])
        executor_username = connection.user.username
        workspace_key = cls._workspace_key(
            user['username'],
            test_env,
            executor_username,
            workspace_type,
            resource_id,
        )
        existing = cls._active_workspace(workspace_key, str(connection.connection_id))
        if existing:
            lease = ExecutorSlotLeaseService.acquire(
                user=user,
                connection=connection,
                runtime_type=workspace_type,
                resource_id=resource_id,
                workspace_id=existing.workspace_id,
            )
            existing.updated_at = datetime.now()
            existing.detached_at = None
            cls._apply_lease(existing, lease)
            runtime_model = cls._runtime_model(user, workspace_type, resource_id, test_env)
            runtime_model.workspace_id = existing.workspace_id
            runtime_model.slot_id = existing.slot_id
            runtime_model.executor_connection_id = existing.connection_id
            runtime_model.send_user = user['username']
            existing.runtime_data = runtime_model.model_dump()
            existing.status = "initializing"
            existing.error_message = ""
            cls._save_record(existing)
            log.ui.info(
                f"UI实时工作区复用：workspace={existing.workspace_id}，"
                f"user={user['username']}，executor={executor_username}，"
                f"type={workspace_type}，resource={resource_id}，connection={connection.connection_id}"
            )
            cls._send_workspace_start(executor_username, existing, runtime_model.model_dump())
            return cls._payload(existing, reused=True, actuators=cls.available_actuators(user))

        workspace_id = str(uuid.uuid4())
        lease = ExecutorSlotLeaseService.acquire(
            user=user,
            connection=connection,
            runtime_type=workspace_type,
            resource_id=resource_id,
            workspace_id=workspace_id,
        )
        runtime_model = cls._runtime_model(user, workspace_type, resource_id, test_env)
        runtime_model.workspace_id = workspace_id
        runtime_model.slot_id = lease["slot_id"]
        runtime_model.executor_connection_id = str(connection.connection_id)
        runtime_model.send_user = user['username']
        record = LiveWorkspaceRecord(
            workspace_id=workspace_id,
            workspace_type=workspace_type,
            resource_id=resource_id,
            test_env=test_env,
            username=user['username'],
            executor_username=executor_username,
            connection_id=str(connection.connection_id),
            user_id=int(user["id"]),
            slot_id=lease["slot_id"],
            idle_deadline=lease["idle_deadline"],
            active_user_count=lease["active_user_count"],
            max_user_count=lease["max_user_count"],
            available_user_count=lease["available_user_count"],
            runtime_data=runtime_model.model_dump(),
        )
        with cls._lock:
            old_record = cls._get_workspace_by_key(workspace_key)
            if old_record:
                cls._delete_record(old_record)
            cls._save_record(record)
        log.ui.info(
            f"UI实时工作区创建：workspace={workspace_id}，user={user['username']}，"
            f"executor={executor_username}，type={workspace_type}，resource={resource_id}，"
            f"connection={connection.connection_id}"
        )
        cls._send_workspace_start(executor_username, record, runtime_model.model_dump())
        return cls._payload(record, reused=False, actuators=cls.available_actuators(user))

    @staticmethod
    def _runtime_model(user: dict, workspace_type: str, resource_id: int, test_env: int):
        test_case = TestCase(
            user['id'],
            user['username'],
            test_env,
            is_send=False,
        )
        if workspace_type == LiveStreamExecutionType.ELEMENT_WORKSPACE.value:
            return test_case.workspace_page_model(resource_id)
        if workspace_type == LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value:
            runtime_model = test_case.debug_steps_model(resource_id, mark_running=False)
            runtime_model.ui_auth_cache = test_case.ui_auth_cache(runtime_model.project_product)
            return runtime_model
        raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_TYPE_UNSUPPORTED)

    @classmethod
    def _send_workspace_start(cls, executor_username: str, record: LiveWorkspaceRecord, runtime_data: dict) -> None:
        cls._send_command(
            executor_username,
            LiveStreamCommand.WORKSPACE_START.value,
            {
                "workspace_id": record.workspace_id,
                "workspace_type": record.workspace_type,
                "resource_id": record.resource_id,
                "test_env": record.test_env,
                "slot_id": record.slot_id,
                "idle_timeout_seconds": ExecutorSlotLeaseService.IDLE_TIMEOUT_SECONDS,
                "idle_deadline": record.idle_deadline,
                "runtime_data": runtime_data,
            },
            # 每次打开/复用都需要执行器重新回传 ready；执行器侧按 workspace_id 幂等复用浏览器。
            message_key=(
                f"live-workspace:start:{record.workspace_id}:{record.connection_id}:"
                f"{int(record.updated_at.timestamp() * 1000000)}"
            ),
        )

    @classmethod
    def available_actuators(cls, user: dict) -> list[dict]:
        return [
            cls._actuator_payload(connection, is_owner=connection.user_id == int(user['id']))
            for connection in SocketConnectionService.list_online_actuators()
            if connection.user_id == int(user['id']) or connection.is_open
        ]

    @classmethod
    def close_workspace(cls, user: dict, workspace_id: str, force: bool = False) -> dict:
        if not workspace_id:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_REQUIRED)
        record = cls._get_record(str(workspace_id))
        if record and record.username != user['username']:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED)
        if record is None:
            return {"workspace_id": workspace_id, "status": "closed"}
        if record and not force:
            record.detached_at = datetime.now()
            record.updated_at = record.detached_at
            cls._save_record(record)
            return {
                "workspace_id": workspace_id,
                "status": "detached",
                "keep_alive_seconds": cls._keep_alive_seconds,
            }
        status = "closing"
        try:
            cls._send_command(
                record.executor_username,
                LiveStreamCommand.WORKSPACE_STOP.value,
                {
                    "workspace_id": workspace_id,
                    "reason": "user_closed",
                },
                message_key=f"live-workspace:stop:{record.workspace_id}:{record.connection_id}",
            )
        except Exception as error:
            status = "closed"
            log.ui.warning(
                f"UI实时工作区关闭命令未送达，按已关闭清理：workspace={workspace_id}，"
                f"executor={record.executor_username}，error={type(error).__name__}"
            )
        finally:
            cls._remove_workspace(str(workspace_id))
        return {"workspace_id": workspace_id, "status": status}

    @classmethod
    def _active_workspace(cls, workspace_key: str, connection_id: str) -> LiveWorkspaceRecord | None:
        cls._cleanup_expired()
        with cls._lock:
            record = cls._get_workspace_by_key(workspace_key)
            if not record:
                return None
            if record.connection_id != connection_id:
                cls._remove_workspace(record.workspace_id)
                return None
            if record.detached_at and datetime.now() - record.detached_at > timedelta(seconds=cls._keep_alive_seconds):
                cls._remove_workspace(record.workspace_id)
                return None
            return record

    @classmethod
    def _cleanup_expired(cls) -> None:
        now = datetime.now()
        with cls._lock:
            expired_records = [
                record
                for record in cls._workspace_by_id.values()
                if record.detached_at and now - record.detached_at > timedelta(seconds=cls._keep_alive_seconds)
            ]
            for record in expired_records:
                cls._remove_workspace(record.workspace_id)
        for record in expired_records:
            try:
                cls._send_command(
                    record.executor_username,
                    LiveStreamCommand.WORKSPACE_STOP.value,
                    {
                        "workspace_id": record.workspace_id,
                        "reason": "keep_alive_expired",
                    },
                    message_key=f"live-workspace:stop:{record.workspace_id}:{record.connection_id}",
                )
            except Exception:
                pass

    @classmethod
    def get_workspace(cls, workspace_id: str) -> LiveWorkspaceRecord | None:
        cls._cleanup_expired()
        record = cls._get_record(str(workspace_id))
        if not record:
            return None
        if record.detached_at and datetime.now() - record.detached_at > timedelta(seconds=cls._keep_alive_seconds):
            cls._remove_workspace(record.workspace_id)
            return None
        try:
            connection = SocketConnectionService.require_actuator(record.executor_username)
        except Exception:
            cls._remove_workspace(record.workspace_id)
            return None
        if str(connection.connection_id) != str(record.connection_id):
            ExecutorSlotLeaseService.release(
                record.connection_id,
                slot_id=record.slot_id,
                user_id=record.user_id,
            )
            record.connection_id = str(connection.connection_id)
            lease = ExecutorSlotLeaseService.acquire(
                user={"id": record.user_id, "username": record.username},
                connection=connection,
                runtime_type=record.workspace_type,
                resource_id=record.resource_id,
                workspace_id=record.workspace_id,
            )
            cls._apply_lease(record, lease)
            if record.runtime_data is not None:
                record.runtime_data["slot_id"] = record.slot_id
                record.runtime_data["executor_connection_id"] = record.connection_id
            record.detached_at = None
            record.updated_at = datetime.now()
            log.ui.info(
                f"UI实时工作区执行器重连后恢复：workspace={record.workspace_id}，"
                f"user={record.username}，executor={record.executor_username}，"
                f"type={record.workspace_type}，resource={record.resource_id}，"
                f"connection={connection.connection_id}"
            )
            cls._send_workspace_start(record.executor_username, record, record.runtime_data or {})
            cls._save_record(record)
        return record

    @classmethod
    def ensure_workspace_started(cls, workspace_id: str) -> LiveWorkspaceRecord | None:
        record = cls.get_workspace(workspace_id)
        if record is None:
            return None
        log.ui.info(
            f"UI实时工作区启动确认：workspace={record.workspace_id}，"
            f"executor={record.executor_username}，type={record.workspace_type}，resource={record.resource_id}"
        )
        return record

    @classmethod
    def update_workspace_status(
            cls,
            workspace_id: str,
            status: str,
            message: str = "",
    ) -> LiveWorkspaceRecord | None:
        if status not in ("initializing", "ready", "failed", "closed"):
            return None
        record = cls._get_record(str(workspace_id))
        if record is None:
            return None
        record.status = status
        record.error_message = str(message or "")
        record.updated_at = datetime.now()
        if status == "closed":
            cls._delete_record(record)
        else:
            cls._save_record(record)
        return record

    @classmethod
    def workspace_status(cls, user: dict, workspace_id: str) -> dict:
        record = cls._get_record(str(workspace_id))
        if record is None:
            return {
                "workspace_id": str(workspace_id),
                "status": "closed",
                "message": "实时工作区不存在或已过期",
            }
        if record.username != user.get("username"):
            raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_ACCESS_DENIED_CODE_ACCESS_DENIED)
        return {
            "workspace_id": record.workspace_id,
            "status": record.status,
            "message": record.error_message,
            "executor_username": record.executor_username,
            "idle_deadline": record.idle_deadline,
            "updated_at": record.updated_at,
        }

    @classmethod
    def _remove_workspace(cls, workspace_id: str) -> None:
        with cls._lock:
            record = cls._get_record(workspace_id)
            if record:
                ExecutorSlotLeaseService.touch(
                    record.connection_id,
                    slot_id=record.slot_id,
                )
                cls._delete_record(record)

    @classmethod
    def _get_record(cls, workspace_id: str) -> LiveWorkspaceRecord | None:
        if cls._use_local_store():
            return cls._workspace_by_id.get(str(workspace_id))
        data = cache.get(cls._record_cache_key(str(workspace_id)))
        return cls._record_from_data(data) if data else None

    @classmethod
    def _get_workspace_by_key(cls, workspace_key: str) -> LiveWorkspaceRecord | None:
        if cls._use_local_store():
            return cls._workspace_by_key.get(workspace_key)
        workspace_id = cache.get(cls._index_cache_key(workspace_key))
        if not workspace_id:
            return None
        record = cls._get_record(str(workspace_id))
        if record is None:
            cache.delete(cls._index_cache_key(workspace_key))
        return record

    @classmethod
    def _save_record(cls, record: LiveWorkspaceRecord) -> None:
        workspace_key = cls._workspace_key(
            record.username,
            record.test_env,
            record.executor_username,
            record.workspace_type,
            record.resource_id,
        )
        if cls._use_local_store():
            cls._workspace_by_id[record.workspace_id] = record
            cls._workspace_by_key[workspace_key] = record
            return
        cache.set(
            cls._record_cache_key(record.workspace_id),
            cls._record_to_data(record),
            timeout=cls._cache_ttl_seconds,
        )
        cache.set(
            cls._index_cache_key(workspace_key),
            record.workspace_id,
            timeout=cls._cache_ttl_seconds,
        )

    @classmethod
    def _delete_record(cls, record: LiveWorkspaceRecord) -> None:
        workspace_key = cls._workspace_key(
            record.username,
            record.test_env,
            record.executor_username,
            record.workspace_type,
            record.resource_id,
        )
        if cls._use_local_store():
            cls._workspace_by_id.pop(record.workspace_id, None)
            indexed = cls._workspace_by_key.get(workspace_key)
            if indexed and indexed.workspace_id == record.workspace_id:
                cls._workspace_by_key.pop(workspace_key, None)
            return
        indexed_workspace_id = cache.get(cls._index_cache_key(workspace_key))
        cache.delete(cls._record_cache_key(record.workspace_id))
        if str(indexed_workspace_id or "") == record.workspace_id:
            cache.delete(cls._index_cache_key(workspace_key))

    @staticmethod
    def _record_to_data(record: LiveWorkspaceRecord) -> dict:
        return {
            **record.__dict__,
            "created_at": record.created_at.timestamp(),
            "updated_at": record.updated_at.timestamp(),
            "detached_at": record.detached_at.timestamp() if record.detached_at else None,
        }

    @staticmethod
    def _record_from_data(data: dict) -> LiveWorkspaceRecord:
        values = dict(data)
        values.setdefault("status", "initializing")
        values.setdefault("error_message", "")
        values["created_at"] = datetime.fromtimestamp(float(values["created_at"]))
        values["updated_at"] = datetime.fromtimestamp(float(values["updated_at"]))
        detached_at = values.get("detached_at")
        values["detached_at"] = datetime.fromtimestamp(float(detached_at)) if detached_at else None
        return LiveWorkspaceRecord(**values)

    @staticmethod
    def _record_cache_key(workspace_id: str) -> str:
        return f'{LIVE_WORKSPACE_RECORD_KEY_PREFIX}{workspace_id}'

    @staticmethod
    def _index_cache_key(workspace_key: str) -> str:
        return f"ui-live-workspace:index:{workspace_key}"

    @staticmethod
    def _use_local_store() -> bool:
        return "test" in sys.argv

    @staticmethod
    def _workspace_key(
            username: str,
            test_env: int,
            executor_username: str,
            workspace_type: str,
            resource_id: int,
    ) -> str:
        return f"{username}:{test_env}:{executor_username}:{workspace_type}:{resource_id}"

    @staticmethod
    def _payload(record: LiveWorkspaceRecord, reused: bool, actuators: list[dict] | None = None) -> dict:
        return {
            "workspace_id": record.workspace_id,
            "workspace_type": record.workspace_type,
            "resource_id": record.resource_id,
            "test_env": record.test_env,
            "execution_type": record.workspace_type,
            "execution_id": record.workspace_id,
            "client": "执行器",
            "executor_username": record.executor_username,
            "actuators": actuators or [],
            "reused": reused,
            "keep_alive_seconds": LiveWorkspaceService._keep_alive_seconds,
            "slot_id": record.slot_id,
            "idle_deadline": record.idle_deadline,
            "idle_timeout_seconds": ExecutorSlotLeaseService.IDLE_TIMEOUT_SECONDS,
            "active_user_count": record.active_user_count,
            "max_user_count": record.max_user_count,
            "available_user_count": record.available_user_count,
            "status": record.status,
            "message": record.error_message,
        }

    @classmethod
    def _resolve_executor(cls, user: dict, actuator_username: str | None):
        requested_username = (actuator_username or '').strip()
        current_username = user['username']
        if requested_username:
            connection = SocketConnectionService.require_actuator(requested_username)
            if requested_username != current_username and not connection.is_open:
                raise AutoUiError(AUTO_UI_LIVE_STREAM_WORKSPACE_SERVICE_EXECUTOR_USER_EXECUTION_INVALID)
            return connection
        try:
            return SocketConnectionService.require_actuator(current_username)
        except Exception:
            return None

    @staticmethod
    def _actuator_payload(connection, is_owner: bool = False) -> dict:
        occupancy = ExecutorSlotLeaseService.occupancy(connection)
        return {
            "username": connection.user.username,
            "name": connection.user.name,
            "ip": connection.user.ip,
            "connection_id": str(connection.connection_id),
            "is_open": connection.is_open,
            "web_live_stream_supported": connection.web_live_stream_supported,
            "is_owner": is_owner,
            "last_seen_at": connection.last_seen_at,
            **occupancy,
        }

    @staticmethod
    def _apply_lease(record: LiveWorkspaceRecord, lease: dict) -> None:
        record.slot_id = lease["slot_id"]
        record.idle_deadline = lease["idle_deadline"]
        record.active_user_count = lease["active_user_count"]
        record.max_user_count = lease["max_user_count"]
        record.available_user_count = lease["available_user_count"]

    @staticmethod
    def _send_command(
            username: str,
            func_name: str,
            func_args: dict,
            *,
            message_key: str,
    ) -> None:
        SocketConnectionService.require_actuator(username)
        SocketMessageService.send_socket_data(
            SocketEnvelopeContract(
                code=200,
                msg="UI实时工作区命令已发送",
                user=username,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(func_name=func_name, func_args=func_args),
            ),
            message_key=message_key,
            ttl_seconds=REALTIME_COMMAND_TTL_SECONDS,
        )
