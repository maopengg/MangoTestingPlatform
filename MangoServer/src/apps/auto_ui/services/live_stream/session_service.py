import uuid

from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract

from src.apps.auto_ui.enums.live_stream import (
    LiveStreamCommand,
    LiveStreamExecutionType,
    LiveStreamRole,
)
from src.apps.auto_ui.exceptions import (
    AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_USER_EXECUTION_INVALID,
    AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_EXECUTION_INVALID,
    AUTO_UI_LIVE_STREAM_SESSION_SERVICE_ACCESS_DENIED,
    AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND,
    AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND_CODE_NOT_FOUND,
    AUTO_UI_LIVE_STREAM_SESSION_WORKSPACE_EXPIRED,
    AutoUiError,
)
from src.apps.auto_ui.services.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.live_stream.constants import REALTIME_COMMAND_TTL_SECONDS
from src.apps.auto_ui.services.live_stream.permission_service import LiveStreamPermissionService
from src.apps.auto_ui.services.live_stream.session_store import LiveStreamSessionStore
from src.apps.auto_ui.services.live_stream.token_service import LiveStreamTokenService
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.common.logging import log


class LiveStreamSessionService:
    DEFAULT_CONFIG = {
        "fps": 3,
        "quality": 55,
        "max_width": 1280,
        "max_height": 720,
    }

    @classmethod
    def create_session(
            cls,
            user: dict,
            execution_type: str,
            execution_id: str,
            resource_id: str | None = None,
            read_only: bool = False,
            actuator_username: str | None = None,
    ) -> dict:
        LiveStreamPermissionService.validate_execution(execution_type, resource_id or execution_id)
        executor_username = cls._resolve_executor_username(user, execution_type, execution_id, actuator_username)
        connection = SocketConnectionService.require_actuator(executor_username)
        if execution_type in (
                LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
                LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
        ):
            from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

            workspace = LiveWorkspaceService.get_workspace(execution_id)
            if workspace is None:
                raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND)
            slot = {
                "slot_id": workspace.slot_id,
                "idle_deadline": workspace.idle_deadline,
                "idle_timeout_seconds": ExecutorSlotLeaseService.IDLE_TIMEOUT_SECONDS,
            }
        else:
            slot = ExecutorSlotLeaseService.acquire(
                user=user,
                connection=connection,
                runtime_type=execution_type,
                resource_id=resource_id or execution_id,
                workspace_id=str(execution_id),
            )
        stream_id = str(uuid.uuid4())
        claims = cls._claims(
            stream_id,
            user,
            executor_username,
            execution_type,
            execution_id,
            str(connection.connection_id),
            resource_id,
            read_only,
            slot,
        )
        LiveStreamSessionStore.create(claims)
        log.ui.info(
            f"UI直播会话创建：stream={stream_id}，user={user.get('username')}，"
            f"executor={executor_username}，type={execution_type}，execution={execution_id}，"
            f"resource={resource_id}，connection={connection.connection_id}"
        )
        return {
            "stream_id": stream_id,
            "status": "created",
            "subscribe_url": f"/ws/ui-stream/subscribe/{stream_id}",
            "config": dict(cls.DEFAULT_CONFIG),
            "slot_id": slot["slot_id"],
            "idle_deadline": slot["idle_deadline"],
            "idle_timeout_seconds": slot["idle_timeout_seconds"],
        }

    @classmethod
    def _resolve_executor_username(
            cls,
            user: dict,
            execution_type: str,
            execution_id: str,
            actuator_username: str | None = None,
    ) -> str:
        executor_username = user.get("username")
        if execution_type in ("element_workspace", "page_step_workspace"):
            from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

            workspace = LiveWorkspaceService.get_workspace(execution_id)
            if workspace is None or workspace.username != user.get("username"):
                log.ui.warning(
                    f"UI直播会话创建失败，工作区不存在：user={user.get('username')}，"
                    f"type={execution_type}，execution={execution_id}"
                )
                raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_SERVICE_NOT_FOUND_CODE_NOT_FOUND)
            return workspace.executor_username
        requested_username = (actuator_username or '').strip()
        if not requested_username:
            return executor_username
        connection = SocketConnectionService.require_actuator(requested_username)
        if requested_username != user.get("username") and not connection.is_open:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_USER_EXECUTION_INVALID)
        return requested_username

    @classmethod
    def start_session(cls, user: dict, stream_id: str, ready_ticket: str) -> dict:
        ready = LiveStreamTokenService.verify(ready_ticket, LiveStreamRole.READY)
        cls._validate_user_stream(user, stream_id, ready)
        connection = SocketConnectionService.require_actuator(ready["executor_username"])
        if str(connection.connection_id) != ready["connection_id"]:
            log.ui.warning(
                f"UI直播启动失败，执行器连接变化：stream={stream_id}，"
                f"executor={ready['executor_username']}，old={ready['connection_id']}，"
                f"new={connection.connection_id}"
            )
            raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_SERVICE_EXECUTOR_EXECUTION_INVALID)
        if ready["execution_type"] in (
                LiveStreamExecutionType.ELEMENT_WORKSPACE.value,
                LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
        ):
            from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

            workspace = LiveWorkspaceService.ensure_workspace_started(ready["execution_id"])
            if workspace is None:
                raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_WORKSPACE_EXPIRED)
        publish_token = LiveStreamTokenService.issue(ready, LiveStreamRole.PUBLISHER)
        if ready.get("slot_id"):
            ExecutorSlotLeaseService.set_live(
                ready["connection_id"],
                ready["slot_id"],
                True,
                stream_id=stream_id,
            )
        command = SocketEnvelopeContract(
            code=200,
            msg="开始UI浏览器实时画面",
            user=ready["executor_username"],
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=LiveStreamCommand.START.value,
                func_args={
                    "stream_id": stream_id,
                    "execution_type": ready["execution_type"],
                    "execution_id": ready["execution_id"],
                    "send_user": user["username"],
                    "publish_path": f"/ws/ui-stream/publish/{stream_id}",
                    "publish_token": publish_token,
                    "slot_id": ready.get("slot_id"),
                    "idle_timeout_seconds": ready.get(
                        "idle_timeout_seconds",
                        ExecutorSlotLeaseService.IDLE_TIMEOUT_SECONDS,
                    ),
                    "idle_deadline": ready.get("idle_deadline"),
                    "config": dict(cls.DEFAULT_CONFIG),
                },
            ),
        )
        try:
            SocketMessageService.send_socket_data(
                command,
                message_key=f"live-stream:start:{stream_id}",
                ttl_seconds=REALTIME_COMMAND_TTL_SECONDS,
            )
        except Exception:
            if ready.get("slot_id"):
                ExecutorSlotLeaseService.set_live(
                    ready["connection_id"],
                    ready["slot_id"],
                    False,
                    stream_id=stream_id,
                )
            raise
        log.ui.info(
            f"UI直播启动命令已发送：stream={stream_id}，executor={ready['executor_username']}，"
            f"type={ready['execution_type']}，execution={ready['execution_id']}，"
            f"connection={connection.connection_id}"
        )
        return {"stream_id": stream_id, "status": "waiting_publisher"}

    @classmethod
    def close_session(cls, user: dict, stream_id: str) -> dict:
        claims = LiveStreamSessionStore.get_claims(stream_id)
        cls._validate_user_stream(user, stream_id, claims)
        SocketMessageService.send_socket_data(
            SocketEnvelopeContract(
                code=200,
                msg="停止UI浏览器实时画面",
                user=claims["executor_username"],
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(
                    func_name=LiveStreamCommand.STOP.value,
                    func_args={"stream_id": stream_id, "reason": "user_closed"},
                ),
            ),
            message_key=f"live-stream:stop:{stream_id}",
            ttl_seconds=REALTIME_COMMAND_TTL_SECONDS,
        )
        LiveStreamSessionStore.close(stream_id)
        if claims.get("slot_id"):
            ExecutorSlotLeaseService.set_live(
                claims["connection_id"],
                claims["slot_id"],
                False,
                stream_id=stream_id,
            )
        return {"stream_id": stream_id, "status": "closed"}

    @staticmethod
    def _claims(
            stream_id,
            user,
            executor_username,
            execution_type,
            execution_id,
            connection_id,
            resource_id=None,
            read_only=False,
            slot=None,
    ) -> dict:
        return {
            "stream_id": stream_id,
            "user_id": int(user["id"]),
            "executor_username": executor_username,
            "connection_id": connection_id,
            "execution_type": execution_type,
            "execution_id": str(execution_id),
            "resource_id": str(resource_id or execution_id),
            "read_only": bool(read_only),
            "slot_id": slot["slot_id"],
            "idle_deadline": slot["idle_deadline"],
            "idle_timeout_seconds": slot["idle_timeout_seconds"],
        }

    @staticmethod
    def _validate_user_stream(user: dict, stream_id: str, claims: dict) -> None:
        if claims.get("stream_id") != stream_id or int(claims.get("user_id", 0)) != int(user["id"]):
            raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_SERVICE_ACCESS_DENIED)
