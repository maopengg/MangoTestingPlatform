import uuid
from urllib.parse import parse_qsl

import jwt
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from mangotools.contracts import SocketEnvelopeContract
from mangotools.enums import ActuatorPytestEventEnum
from uvicorn.protocols.utils import ClientDisconnected

from src.apps.system.enums import ClientNameEnum, ClientTypeEnum, SocketEnum
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.consumer import ServerInterfaceReflection
from src.apps.user.selectors.querysets import UserQuerySelector
from src.common.decorators.system_error import areport_system_error, system_error_guard
from src.common.logging import log
from src.common.responses.response_msg import RESPONSE_MSG_0210
from src.processes.realtime.registry import LocalConnection, LocalConnectionRegistry


class RealtimeConsumer(AsyncJsonWebsocketConsumer):
    SERVER_CALLBACK_NOTICE_FUNCTIONS = {
        "u_live_workspace_status",
        "u_page_steps",
        "u_test_case",
        "u_test_suite_details",
        ActuatorPytestEventEnum.TEST_CASE.value,
        ActuatorPytestEventEnum.TEST_CASE_BATCH.value,
    }

    def __init__(self, *args, registry: LocalConnectionRegistry, service_instance: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = registry
        self.service_instance = service_instance
        self.reflection = ServerInterfaceReflection()
        self.user_id = 0
        self.username = ""
        self.client_type = 0
        self.connection_id = ""
        self.local_channel_name = ""
        self.websocket_accepted = False

    @system_error_guard(
        source=SystemErrorEventSource.REALTIME,
        request_path='connect_realtime_client',
        service_name=RuntimeServiceName.REALTIME,
    )
    async def connect(self):
        identity = await self._verify_user()
        if identity is None:
            await self.close(code=4401)
            return
        self.user_id, self.username = identity
        self.client_type = self._client_type()
        if not self.client_type:
            await self.close(code=4404)
            return
        try:
            await self._accept_once()
        except ClientDisconnected:
            log.system.debug(
                f"实时连接握手期间客户端已断开：user={self.username}, "
                f"client_type={self.client_type}"
            )
            return
        self.local_channel_name = getattr(self, "channel_name", "") or f"local.{uuid.uuid4().hex}"
        try:
            registration = await database_sync_to_async(SocketConnectionService.register)(
                user_id=self.user_id,
                client_type=self.client_type,
                channel_name=self.local_channel_name,
                service_instance=self.service_instance,
            )
            self.connection_id = str(registration.connection.connection_id)
            await self._join_notification_groups()
            replaced = await self.registry.register(
                LocalConnection(
                    connection_id=self.connection_id,
                    user_id=self.user_id,
                    username=self.username,
                    client_type=self.client_type,
                    consumer=self,
                )
            )
            await self._close_replaced_connection(replaced)
            await self.send_json(
                {
                    "protocol_version": 1,
                    "connection_id": self.connection_id,
                    "code": 200,
                    "msg": self._connected_message(),
                    "user": self.username,
                    "is_notice": None,
                    "data": None,
                }
            )
            if self.client_type == ClientTypeEnum.ACTUATOR.value:
                await self._notify_web(
                    f"您的{ClientNameEnum.DRIVER.value}已连接上{ClientNameEnum.SERVER.value}！"
                )
            log.system.info(
                f"实时连接已建立：user={self.username}, client_type={self.client_type}, "
                f"connection_id={self.connection_id}"
            )
        except ClientDisconnected:
            await self._cleanup_connection()
            log.system.debug(
                f"实时连接建立期间客户端已断开：user={self.username}, "
                f"client_type={self.client_type}"
            )
            return
        except BaseException:
            await self._cleanup_connection()
            raise

    async def _accept_once(self) -> None:
        """接受 WebSocket 握手，并兼容服务器已完成接受的竞争状态。"""
        if self.websocket_accepted:
            return
        try:
            await self.accept()
        except RuntimeError as error:
            message = str(error)
            already_accepted = all(
                value in message
                for value in ("websocket.accept", "websocket.send", "websocket.close")
            )
            if not already_accepted:
                raise
            log.system.debug(
                f"实时连接已由 ASGI 服务器完成握手，跳过重复 accept："
                f"user={self.username}, client_type={self.client_type}"
            )
        self.websocket_accepted = True

    async def disconnect(self, close_code):
        was_registered = await self._cleanup_connection()
        if was_registered and self.client_type == ClientTypeEnum.ACTUATOR.value and self.username:
            await self._notify_web(f"{ClientNameEnum.DRIVER.value}已断开！")

    async def _close_replaced_connection(self, replaced: LocalConnection | None) -> None:
        if replaced is None:
            return
        try:
            await replaced.consumer.close(code=4001)
        except Exception as error:
            log.system.warning(
                f"旧实时连接已关闭，跳过重复关闭：connection_id={replaced.connection_id}, "
                f"error={error}"
            )

    async def _cleanup_connection(self) -> bool:
        connection_id = self.connection_id
        if not connection_id:
            return False
        self.connection_id = ""
        await self._leave_notification_groups()
        registered = await self.registry.unregister(connection_id)
        try:
            await database_sync_to_async(SocketConnectionService.disconnect)(connection_id)
            if self.client_type == ClientTypeEnum.ACTUATOR.value:
                from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService

                await database_sync_to_async(ExecutorSlotLeaseService.clear_connection)(connection_id)
        except Exception as error:
            await areport_system_error(
                error,
                source=SystemErrorEventSource.REALTIME,
                request_path='cleanup_realtime_connection',
                service_name=RuntimeServiceName.REALTIME,
            )
            log.system.error(
                f"实时连接数据库状态清理失败：connection_id={connection_id}, error={error}"
            )
        return registered is not None

    async def _join_notification_groups(self) -> None:
        channel_layer = getattr(self, "channel_layer", None)
        if not channel_layer or not self.local_channel_name:
            return
        await channel_layer.group_add(
            f"mango.realtime.user.{self.client_type}.{self.user_id}",
            self.local_channel_name,
        )
        await channel_layer.group_add(
            f"mango.realtime.client.{self.client_type}",
            self.local_channel_name,
        )

    async def _leave_notification_groups(self) -> None:
        channel_layer = getattr(self, "channel_layer", None)
        if not channel_layer or not self.local_channel_name:
            return
        await channel_layer.group_discard(
            f"mango.realtime.user.{self.client_type}.{self.user_id}",
            self.local_channel_name,
        )
        await channel_layer.group_discard(
            f"mango.realtime.client.{self.client_type}",
            self.local_channel_name,
        )

    async def socket_notification(self, event: dict) -> None:
        payload = event.get("payload")
        if isinstance(payload, dict):
            await self.send_json(payload)

    @system_error_guard(
        source=SystemErrorEventSource.REALTIME,
        request_path='receive_realtime_message',
        service_name=RuntimeServiceName.REALTIME,
    )
    async def receive_json(self, content, **kwargs):
        if not self.connection_id:
            await self.close(code=4401)
            return
        await self.registry.touch(self.connection_id)
        try:
            socket_data = SocketEnvelopeContract(**content)
        except Exception as error:
            log.system.warning(f"实时消息格式错误：user={self.username}, error={error}")
            await self.send_json({"code": 400, "msg": "消息格式错误", "data": None})
            return
        if self.client_type != ClientTypeEnum.ACTUATOR.value and (socket_data.data or socket_data.is_notice is not None):
            await self.send_json({'code': 403, 'msg': RESPONSE_MSG_0210[1], 'data': None})
            return
        if socket_data.is_notice is not None:
            if (
                    socket_data.data
                    and socket_data.data.func_name in self.SERVER_CALLBACK_NOTICE_FUNCTIONS
            ):
                socket_data.data.message_id = socket_data.message_id
                self.reflection.server_data_received.send(
                    sender="websocket",
                    data=socket_data.data,
                )
            await self._relay(socket_data)
        elif socket_data.data and socket_data.data.func_name:
            socket_data.data.message_id = socket_data.message_id
            self.reflection.server_data_received.send(sender="websocket", data=socket_data.data)

    async def _relay(self, socket_data: SocketEnvelopeContract) -> None:
        if socket_data.is_notice == ClientTypeEnum.WEB.value:
            target_user = await self._resolve_user_id(socket_data.user or self.username)
            if target_user is not None:
                for connection in await self.registry.get_web_connections(target_user):
                    await connection.consumer.send_json(socket_data.model_dump(mode="json"))
        elif socket_data.is_notice == ClientTypeEnum.ACTUATOR.value:
            target_user = await self._resolve_user_id(socket_data.user or self.username)
            if target_user is not None:
                connection = await self.registry.get_actuator(target_user)
                if connection is not None:
                    await connection.consumer.send_json(socket_data.model_dump(mode="json"))

    async def _notify_web(self, message: str) -> None:
        payload = SocketEnvelopeContract(
            code=200,
            msg=message,
            user=self.username,
            is_notice=ClientTypeEnum.WEB,
            data=None,
        )
        for connection in await self.registry.get_web_connections(self.user_id):
            await connection.consumer.send_json(payload.model_dump(mode="json"))

    @database_sync_to_async
    def _resolve_user_id(self, username: str) -> int | None:
        return UserQuerySelector.user().filter(username=username).values_list("id", flat=True).first()

    def _client_type(self) -> int:
        path = self.scope.get("path") or ""
        if path == SocketEnum.WEB_PATH.value:
            return ClientTypeEnum.WEB.value
        if path == SocketEnum.CLIENT_PATH.value:
            return ClientTypeEnum.ACTUATOR.value
        return 0

    def _connected_message(self) -> str:
        if self.client_type == ClientTypeEnum.ACTUATOR.value:
            return f"您的{ClientNameEnum.DRIVER.value}已连接上{ClientNameEnum.SERVER.value}！"
        client = self.scope.get("client") or ("", "")
        return f"心跳已连接！IP：{client[0]}，端口：{client[1]}"

    @database_sync_to_async
    def _verify_user(self) -> tuple[int, str] | None:
        params = dict(parse_qsl((self.scope.get("query_string") or b"").decode()))
        headers = dict(self.scope.get("headers") or [])
        token = (headers.get(b"authorization") or b"").decode() or params.get("token") or ""
        if token:
            identity = self._verify_token(token, self._client_type())
            if identity is not None:
                return identity
        username = (params.get("username") or "").strip()
        password_digest = params.get("password") or ""
        if not username or not password_digest:
            return None
        try:
            from src.apps.user.services.authentication.password import verify_password_digest

            user = UserQuerySelector.user().get(username=username)
            valid_password, upgraded_password = verify_password_digest(password_digest, user.password)
            if not valid_password:
                return None
            if upgraded_password:
                user.password = upgraded_password
                user.save(update_fields=["password"])
            return user.id, user.username
        except UserQuerySelector.user().model.DoesNotExist:
            return None

    @staticmethod
    def _verify_token(token: str, client_type: int) -> tuple[int, str] | None:
        try:
            if token.lower().startswith("bearer "):
                token = token[7:].strip()
            if token.startswith("b'") and token.endswith("'"):
                token = token[2:-1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
            if payload.get("client_type") != client_type:
                return None
            user = UserQuerySelector.user().get(id=payload.get("id"))
            return user.id, user.username
        except Exception:
            return None
