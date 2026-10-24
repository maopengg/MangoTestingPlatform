from urllib.parse import parse_qsl

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core import signing

from src.apps.auto_ui.enums.live_stream import LiveStreamEvent, LiveStreamRole
from src.apps.auto_ui.services.live_stream.session_store import LiveStreamSessionStore
from src.apps.auto_ui.services.live_stream.token_service import LiveStreamTokenService
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.processes.realtime.auth import RealtimeJwtAuthentication
from src.processes.realtime.live_stream.registry import LiveStreamRegistry


class BaseLiveStreamConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, registry: LiveStreamRegistry, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = registry
        self.stream_id = ""
        self.connection_id = ""
        self._accepted = False

    def token(self) -> str:
        params = dict(parse_qsl((self.scope.get("query_string") or b"").decode()))
        return params.get("token") or ""

    async def protocol_error(self, message: str, close_code: int | None = None) -> None:
        await self.send_json({"type": LiveStreamEvent.ERROR.value, "message": message})
        if close_code:
            await self.close(code=close_code)


class LiveStreamSubscriberConsumer(BaseLiveStreamConsumer):
    async def connect(self):
        self.stream_id = self.scope["url_route"]["kwargs"]["stream_id"]
        try:
            user = await RealtimeJwtAuthentication.authenticate(self.token())
            claims = await database_sync_to_async(LiveStreamSessionStore.get_claims)(self.stream_id)
            if claims.get("stream_id") != self.stream_id:
                raise signing.BadSignature("stream_id不匹配")
            if int(claims.get("user_id", 0)) != int(user["id"]):
                raise signing.BadSignature("无权访问该直播会话")
            await self.accept()
            self._accepted = True
            self.connection_id, ready_ticket = await self.registry.register_subscriber(claims, self)
            await self.send_json({
                "type": LiveStreamEvent.SUBSCRIBER_READY.value,
                "stream_id": self.stream_id,
                "connection_id": self.connection_id,
                "ready_ticket": ready_ticket,
            })
        except Exception as error:
            if not self._accepted:
                await self.accept()
                self._accepted = True
            await self.protocol_error(str(error), 4403)

    async def disconnect(self, close_code):
        if self.connection_id:
            await self.registry.remove_subscriber(self.stream_id, self.connection_id)

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")
        try:
            if event_type == LiveStreamEvent.CONTROL_REQUEST.value:
                result = await self.registry.acquire_control(
                    self.stream_id,
                    self.connection_id,
                )
                await self.send_json({"type": LiveStreamEvent.CONTROL_GRANTED.value, **result})
            elif event_type == LiveStreamEvent.CONTROL_RENEW.value:
                result = await self.registry.renew_control(self.stream_id, self.connection_id)
                await self.send_json({"type": LiveStreamEvent.CONTROL_GRANTED.value, **result})
            elif event_type == LiveStreamEvent.CONTROL_RELEASE.value:
                await self.registry.release_control(self.stream_id, self.connection_id)
            elif event_type == LiveStreamEvent.CONTROL_EVENT.value:
                event_data = content.get("data") or {}
                try:
                    await self.registry.relay_control(self.stream_id, self.connection_id, event_data)
                except Exception as error:
                    await self.send_json({
                        "type": LiveStreamEvent.CONTROL_ACK.value,
                        "sequence": event_data.get("sequence"),
                        "success": False,
                        "message": str(error),
                    })
            else:
                raise RuntimeError("不支持的直播控制消息")
        except Exception as error:
            await self.send_json({"type": LiveStreamEvent.CONTROL_DENIED.value, "message": str(error)})


class LiveStreamPublisherConsumer(BaseLiveStreamConsumer):
    async def connect(self):
        self.stream_id = self.scope["url_route"]["kwargs"]["stream_id"]
        try:
            claims = LiveStreamTokenService.verify(self.token(), LiveStreamRole.PUBLISHER)
            if claims.get("stream_id") != self.stream_id:
                raise signing.BadSignature("stream_id不匹配")
            current_connection = await database_sync_to_async(SocketConnectionService.require_actuator)(
                claims.get("executor_username") or ""
            )
            if str(current_connection.connection_id) != str(claims.get("connection_id")):
                raise signing.BadSignature("执行器连接已被替换")
            await self.accept()
            self._accepted = True
            self.connection_id = await self.registry.register_publisher(claims, self)
            await self.send_json({"type": LiveStreamEvent.PUBLISHER_READY.value, "stream_id": self.stream_id})
        except Exception as error:
            if not self._accepted:
                await self.accept()
                self._accepted = True
            await self.protocol_error(str(error), 4403)

    async def disconnect(self, close_code):
        if self.connection_id:
            await self.registry.remove_publisher(self.stream_id, self.connection_id)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if bytes_data is not None:
            try:
                await self.registry.publish_frame(self.stream_id, self.connection_id, bytes_data)
            except Exception as error:
                await self.protocol_error(str(error), 4400)
            return
        await super().receive(text_data=text_data, bytes_data=bytes_data, **kwargs)

    async def receive_json(self, content, **kwargs):
        await self.registry.relay_publisher_status(self.stream_id, self.connection_id, content)
