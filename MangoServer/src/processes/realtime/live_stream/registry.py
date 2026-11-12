import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import time
from channels.db import database_sync_to_async
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract

from src.apps.auto_ui.enums.live_stream import (
    LiveStreamCommand,
    LiveStreamEvent,
    LiveStreamRole,
)
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.live_stream.constants import REALTIME_COMMAND_TTL_SECONDS
from src.apps.auto_ui.services.live_stream.session_store import LiveStreamSessionStore
from src.apps.auto_ui.services.live_stream.token_service import LiveStreamTokenService
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.common.logging import log
from src.processes.realtime.live_stream.protocol import LiveStreamControlEventValidator


@dataclass
class SubscriberConnection:
    connection_id: str
    user_id: int
    consumer: Any
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    sender_task: asyncio.Task | None = None
    control_events: deque[float] = field(default_factory=deque)
    last_control_sequence: int = 0
    control_event_count: int = 0
    control_event_types: dict[str, int] = field(default_factory=dict)
    pending_control_sequence: int = 0
    pending_control_event_type: str = ""
    pending_control_started_at: float = 0
    pending_control_timeout_task: asyncio.Task | None = None


@dataclass
class StreamState:
    stream_id: str
    claims: dict
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = 0
    publisher: Any | None = None
    publisher_connection_id: str | None = None
    subscribers: dict[str, SubscriberConnection] = field(default_factory=dict)
    controller_id: str | None = None
    control_expires_at: float = 0
    control_started_at: float = 0
    last_control_activity_at: float = 0
    no_viewer_task: asyncio.Task | None = None
    latest_frame: bytes | None = None
    last_frame_at: float = 0
    bandwidth_samples: deque[tuple[float, int]] = field(default_factory=deque)
    published_frames: int = 0
    dropped_frames: int = 0
    published_bytes: int = 0


class LiveStreamRegistry:
    MAX_STREAMS = 100
    MAX_SUBSCRIBERS_PER_STREAM = 5
    MAX_SUBSCRIBERS_TOTAL = 200
    MAX_FRAME_BYTES = 2 * 1024 * 1024
    CONTROL_LEASE_SECONDS = 30
    CONTROL_IDLE_TAKEOVER_SECONDS = 60
    CONTROL_EVENTS_PER_SECOND = 30
    MAX_PUBLISH_FPS = 10
    MAX_STREAM_BYTES_PER_SECOND = 5 * 1024 * 1024
    CONTROL_EVENT_TIMEOUT_SECONDS = 3.0
    CONTROL_COMMAND_TIMEOUT_SECONDS = 15.0
    LONG_RUNNING_CONTROL_EVENTS = {"pick_element", "check_locator"}

    def __init__(self):
        self._streams: dict[str, StreamState] = {}
        self._slot_controllers: dict[str, tuple[str, str]] = {}
        self._lock = asyncio.Lock()
        self._degraded = False
        self._control_events_total = 0
        self._control_events_rejected = 0

    async def register_subscriber(self, claims: dict, consumer: Any) -> tuple[str, str]:
        async with self._lock:
            if self._degraded:
                raise RuntimeError("实时服务当前处于保护降级状态")
            state = self._streams.get(claims["stream_id"])
            if state is None:
                if len(self._streams) >= self.MAX_STREAMS:
                    raise RuntimeError("直播会话容量已满")
                state = StreamState(stream_id=claims["stream_id"], claims=claims)
                self._streams[state.stream_id] = state
            self._validate_claims(state, claims)
            if len(state.subscribers) >= self.MAX_SUBSCRIBERS_PER_STREAM:
                raise RuntimeError("该直播会话观看人数已满")
            if sum(len(item.subscribers) for item in self._streams.values()) >= self.MAX_SUBSCRIBERS_TOTAL:
                raise RuntimeError("实时服务观看连接容量已满")
            connection_id = str(uuid.uuid4())
            subscriber = SubscriberConnection(connection_id, int(claims["user_id"]), consumer)
            subscriber.sender_task = asyncio.create_task(
                self._subscriber_sender(subscriber),
                name=f"live-stream:subscriber:{connection_id}",
            )
            state.subscribers[connection_id] = subscriber
            if state.no_viewer_task:
                state.no_viewer_task.cancel()
                state.no_viewer_task = None
            latest_frame = state.latest_frame
        if latest_frame:
            await self._offer_frame(subscriber, latest_frame)
        ready_ticket = LiveStreamTokenService.issue(claims, LiveStreamRole.READY)
        return connection_id, ready_ticket

    async def register_publisher(self, claims: dict, consumer: Any) -> str:
        async with self._lock:
            if self._degraded:
                raise RuntimeError("实时服务当前处于保护降级状态")
            state = self._streams.get(claims["stream_id"])
            if state is None or not state.subscribers:
                raise RuntimeError("直播会话尚无观看者")
            self._validate_claims(state, claims)
            connection_id = str(uuid.uuid4())
            previous = state.publisher
            state.publisher = consumer
            state.publisher_connection_id = connection_id
        if previous and previous is not consumer:
            await previous.close(code=4001)
        return connection_id

    async def publish_frame(self, stream_id: str, publisher_id: str, frame: bytes) -> int:
        if not frame or len(frame) > self.MAX_FRAME_BYTES:
            raise RuntimeError("直播帧为空或超过大小限制")
        async with self._lock:
            state = self._require_stream(stream_id)
            if state.publisher_connection_id != publisher_id:
                raise RuntimeError("发布连接已失效")
            if self._degraded:
                state.dropped_frames += 1
                return 0
            now = time.monotonic()
            if state.last_frame_at and now - state.last_frame_at < 1 / self.MAX_PUBLISH_FPS:
                state.dropped_frames += 1
                return 0
            while state.bandwidth_samples and now - state.bandwidth_samples[0][0] >= 1:
                state.bandwidth_samples.popleft()
            if sum(size for _, size in state.bandwidth_samples) + len(frame) > self.MAX_STREAM_BYTES_PER_SECOND:
                state.dropped_frames += 1
                return 0
            state.last_frame_at = now
            state.bandwidth_samples.append((now, len(frame)))
            state.latest_frame = frame
            state.published_frames += 1
            state.published_bytes += len(frame)
            subscribers = list(state.subscribers.values())
        await asyncio.gather(*(self._offer_frame(item, frame) for item in subscribers))
        return len(subscribers)

    async def relay_publisher_status(self, stream_id: str, publisher_id: str, payload: dict) -> None:
        async with self._lock:
            state = self._require_stream(stream_id)
            if state.publisher_connection_id != publisher_id:
                raise RuntimeError("发布连接已失效")
            if payload.get("type") == LiveStreamEvent.CONTROL_ACK.value:
                controller = state.subscribers.get(state.controller_id or "")
                sequence = int(payload.get("sequence") or 0)
                if controller is None or controller.pending_control_sequence != sequence:
                    log.system.warning(
                        f"丢弃迟到的UI直播控制结果：stream_id={stream_id}, sequence={sequence}"
                    )
                    return
                self._clear_pending_control(controller)
                consumers = [controller.consumer]
            else:
                consumers = [item.consumer for item in state.subscribers.values()]
        await asyncio.gather(
            *(
                consumer.send_json(
                    payload
                    if payload.get("type") == LiveStreamEvent.CONTROL_ACK.value
                    else {"type": LiveStreamEvent.STREAM_STATUS.value, "data": payload}
                )
                for consumer in consumers
            ),
            return_exceptions=True,
        )

    async def acquire_control(self, stream_id: str, subscriber_id: str) -> dict:
        publisher = None
        audit = None
        for _ in range(3):
            release_target: tuple[str, str, str] | None = None
            async with self._lock:
                state = self._require_stream(stream_id)
                subscriber = state.subscribers.get(subscriber_id)
                if subscriber is None or subscriber.user_id != int(state.claims["user_id"]):
                    raise RuntimeError("控制连接无效")
                if state.claims.get("read_only"):
                    raise RuntimeError("当前实时画面为只读模式，不允许远程控制")
                now = time.monotonic()
                if state.controller_id and state.controller_id != subscriber_id:
                    if state.control_expires_at <= now:
                        release_target = (stream_id, state.controller_id, "lease_expired")
                    elif not self._control_is_idle(state, now):
                        raise RuntimeError("已有其他用户正在控制")
                    else:
                        release_target = (stream_id, state.controller_id, "idle_takeover")
                slot_key = self._control_slot_key(state)
                slot_controller = self._slot_controllers.get(slot_key)
                if release_target is None and slot_controller and slot_controller != (stream_id, subscriber_id):
                    other_state = self._streams.get(slot_controller[0])
                    if other_state and other_state.controller_id == slot_controller[1]:
                        if other_state.control_expires_at <= now:
                            release_target = (*slot_controller, "lease_expired")
                        elif not self._control_is_idle(other_state, now):
                            raise RuntimeError("当前用户已有其他页面正在控制该执行器")
                        else:
                            release_target = (*slot_controller, "idle_takeover")
                    else:
                        self._slot_controllers.pop(slot_key, None)
                if release_target is None:
                    state.controller_id = subscriber_id
                    state.control_expires_at = now + self.CONTROL_LEASE_SECONDS
                    state.control_started_at = now
                    state.last_control_activity_at = now
                    subscriber.control_event_count = 0
                    subscriber.control_event_types.clear()
                    self._slot_controllers[slot_key] = (stream_id, subscriber_id)
                    publisher = state.publisher
                    audit = {
                        "stream_id": stream_id,
                        "subscriber_id": subscriber_id,
                        "user_id": subscriber.user_id,
                    }
                    break
            await self.release_control(*release_target)
        if audit is None:
            raise RuntimeError("直播控制权正在切换，请重试")
        log.system.info(f"UI直播远程控制开始：{audit}")
        if publisher:
            await publisher.send_json({
                "type": LiveStreamEvent.CONTROL_STARTED.value,
                "lease_seconds": self.CONTROL_LEASE_SECONDS,
            })
        return {"lease_seconds": self.CONTROL_LEASE_SECONDS}

    async def renew_control(self, stream_id: str, subscriber_id: str) -> dict:
        publisher = None
        async with self._lock:
            state = self._require_controller(stream_id, subscriber_id)
            now = time.monotonic()
            state.control_expires_at = now + self.CONTROL_LEASE_SECONDS
            publisher = state.publisher
        if publisher:
            await publisher.send_json({
                "type": LiveStreamEvent.CONTROL_STARTED.value,
                "lease_seconds": self.CONTROL_LEASE_SECONDS,
            })
        return {"lease_seconds": self.CONTROL_LEASE_SECONDS}

    async def relay_control(self, stream_id: str, subscriber_id: str, event: dict) -> None:
        try:
            normalized = LiveStreamControlEventValidator.validate(event)
            async with self._lock:
                state = self._require_controller(stream_id, subscriber_id)
                subscriber = state.subscribers[subscriber_id]
                self._check_control_rate(subscriber)
                sequence = normalized["sequence"]
                if sequence <= subscriber.last_control_sequence:
                    raise RuntimeError("远程控制事件序号重复或已过期")
                subscriber.last_control_sequence = sequence
                if subscriber.pending_control_sequence:
                    raise RuntimeError(
                        f"上一项实时控制仍在处理中：sequence={subscriber.pending_control_sequence}"
                    )
                publisher = state.publisher
                if publisher is None:
                    raise RuntimeError("执行器尚未开始推流")
                subscriber.pending_control_sequence = sequence
                subscriber.pending_control_event_type = normalized["event_type"]
                subscriber.pending_control_started_at = time.monotonic()
                state.last_control_activity_at = subscriber.pending_control_started_at
                subscriber.pending_control_timeout_task = asyncio.create_task(
                    self._control_event_timeout(
                        stream_id,
                        subscriber_id,
                        sequence,
                        self._control_timeout_seconds(normalized["event_type"]),
                    ),
                    name=f"live-stream:control-timeout:{stream_id}:{sequence}",
                )
            try:
                await publisher.send_json(
                    {"type": LiveStreamEvent.CONTROL_EVENT.value, "data": normalized}
                )
            except BaseException:
                async with self._lock:
                    state = self._streams.get(stream_id)
                    current = state.subscribers.get(subscriber_id) if state else None
                    if current and current.pending_control_sequence == sequence:
                        self._clear_pending_control(current)
                raise
        except Exception:
            async with self._lock:
                self._control_events_rejected += 1
            raise
        async with self._lock:
            self._control_events_total += 1
            subscriber = state.subscribers.get(subscriber_id)
            if subscriber:
                event_type = normalized["event_type"]
                subscriber.control_event_count += 1
                subscriber.control_event_types[event_type] = (
                        subscriber.control_event_types.get(event_type, 0) + 1
                )
                if event_type == "mouse_click" or subscriber.control_event_count % 20 == 0:
                    log.system.debug(
                        f"UI直播控制事件转发：stream_id={stream_id}, "
                        f"event_type={event_type}, event_count={subscriber.control_event_count}"
                    )

    async def release_control(self, stream_id: str, subscriber_id: str, reason: str = "released") -> None:
        publisher = None
        subscriber_consumer = None
        audit = None
        async with self._lock:
            state = self._streams.get(stream_id)
            if state is None or state.controller_id != subscriber_id:
                return
            subscriber = state.subscribers.get(subscriber_id)
            audit = {
                "stream_id": stream_id,
                "subscriber_id": subscriber_id,
                "user_id": subscriber.user_id if subscriber else None,
                "duration_seconds": round(max(0, time.monotonic() - state.control_started_at), 3),
                "event_count": subscriber.control_event_count if subscriber else 0,
                "event_types": dict(subscriber.control_event_types) if subscriber else {},
                "reason": reason,
            }
            state.controller_id = None
            state.control_expires_at = 0
            state.control_started_at = 0
            state.last_control_activity_at = 0
            publisher = state.publisher
            if subscriber:
                subscriber_consumer = subscriber.consumer
                self._clear_pending_control(subscriber)
            slot_key = self._control_slot_key(state)
            if self._slot_controllers.get(slot_key) == (stream_id, subscriber_id):
                self._slot_controllers.pop(slot_key, None)
        log.system.info(f"UI直播远程控制结束：{audit}")
        stopped_payload = {"type": LiveStreamEvent.CONTROL_STOPPED.value, "reason": reason}
        await asyncio.gather(
            *(
                consumer.send_json(stopped_payload)
                for consumer in (publisher, subscriber_consumer)
                if consumer is not None
            ),
            return_exceptions=True,
        )

    async def remove_subscriber(self, stream_id: str, connection_id: str) -> None:
        sender_task = None
        release_control = False
        async with self._lock:
            state = self._streams.get(stream_id)
            if state is None:
                return
            release_control = state.controller_id == connection_id
            subscriber = state.subscribers.get(connection_id)
            if subscriber:
                sender_task = subscriber.sender_task
                self._clear_pending_control(subscriber)
            if not release_control:
                state.subscribers.pop(connection_id, None)
        if release_control:
            await self.release_control(stream_id, connection_id, "controller_disconnected")
            async with self._lock:
                state = self._streams.get(stream_id)
                if state:
                    state.subscribers.pop(connection_id, None)
        async with self._lock:
            state = self._streams.get(stream_id)
            if state is not None and not state.subscribers and state.no_viewer_task is None:
                state.no_viewer_task = asyncio.create_task(self._close_after_grace(stream_id))
        if sender_task:
            sender_task.cancel()

    async def remove_publisher(self, stream_id: str, connection_id: str) -> None:
        async with self._lock:
            state = self._streams.get(stream_id)
            if state is None or state.publisher_connection_id != connection_id:
                return
            state.publisher = None
            state.publisher_connection_id = None
            consumers = [item.consumer for item in state.subscribers.values()]
        await asyncio.gather(
            *(
                consumer.send_json({
                    "type": LiveStreamEvent.STREAM_STATUS.value,
                    "data": {
                        "status": "disconnected",
                        "message": "执行器实时画面连接已断开",
                    },
                })
                for consumer in consumers
            ),
            return_exceptions=True,
        )

    async def cleanup_expired(self) -> int:
        now = time.monotonic()
        async with self._lock:
            expired = [
                stream_id
                for stream_id, state in self._streams.items()
                if state.expires_at and state.expires_at <= now
            ]
            expired_controls = [
                (state.stream_id, state.controller_id)
                for state in self._streams.values()
                if state.controller_id and state.control_expires_at <= now
            ]
        for stream_id, subscriber_id in expired_controls:
            await self.release_control(stream_id, subscriber_id, "lease_expired")
        for stream_id in expired:
            await self.close_stream(stream_id, "expired")
        return len(expired)

    async def close_stream(self, stream_id: str, reason: str) -> None:
        async with self._lock:
            state = self._streams.pop(stream_id, None)
            if state is not None:
                self._slot_controllers.pop(self._control_slot_key(state), None)
        if state is None:
            return
        if state.no_viewer_task and state.no_viewer_task is not asyncio.current_task():
            state.no_viewer_task.cancel()
        if state.publisher:
            await state.publisher.send_json({"type": LiveStreamEvent.STOP_CAPTURE.value, "reason": reason})
        for subscriber in state.subscribers.values():
            self._clear_pending_control(subscriber)
            if subscriber.sender_task:
                subscriber.sender_task.cancel()
            await subscriber.consumer.close(code=1000)
        if reason != "service_shutdown":
            await self._queue_stop_command(state, reason)
            await database_sync_to_async(LiveStreamSessionStore.close)(stream_id)
        if state.claims.get("slot_id"):
            await database_sync_to_async(ExecutorSlotLeaseService.set_live)(
                state.claims["connection_id"],
                state.claims["slot_id"],
                False,
                stream_id=stream_id,
            )

    async def close_all(self) -> None:
        async with self._lock:
            stream_ids = list(self._streams)
        for stream_id in stream_ids:
            await self.close_stream(stream_id, "service_shutdown")

    async def set_degraded(self, degraded: bool) -> None:
        async with self._lock:
            self._degraded = degraded

    async def stats(self) -> dict:
        async with self._lock:
            return {
                "streams": len(self._streams),
                "publishers": sum(bool(item.publisher) for item in self._streams.values()),
                "subscribers": sum(len(item.subscribers) for item in self._streams.values()),
                "controllers": sum(bool(item.controller_id) for item in self._streams.values()),
                "published_frames": sum(item.published_frames for item in self._streams.values()),
                "dropped_frames": sum(item.dropped_frames for item in self._streams.values()),
                "published_bytes": sum(item.published_bytes for item in self._streams.values()),
                "control_events_total": self._control_events_total,
                "control_events_rejected": self._control_events_rejected,
                "degraded": self._degraded,
            }

    async def _close_after_grace(self, stream_id: str) -> None:
        await asyncio.sleep(10)
        await self.close_stream(stream_id, "no_viewers")

    @staticmethod
    async def _subscriber_sender(subscriber: SubscriberConnection) -> None:
        while True:
            frame = await subscriber.queue.get()
            await asyncio.wait_for(subscriber.consumer.send(bytes_data=frame), timeout=3)

    @staticmethod
    async def _offer_frame(subscriber: SubscriberConnection, frame: bytes) -> None:
        if subscriber.queue.full():
            try:
                subscriber.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        subscriber.queue.put_nowait(frame)

    def _require_stream(self, stream_id: str) -> StreamState:
        state = self._streams.get(stream_id)
        if state is None:
            raise RuntimeError("直播会话不存在或已结束")
        return state

    @staticmethod
    def _control_slot_key(state: StreamState) -> str:
        slot_id = str(state.claims.get("slot_id") or "")
        if slot_id:
            return f"{state.claims.get('connection_id')}:{slot_id}"
        return f"legacy-stream:{state.stream_id}"

    def _require_controller(self, stream_id: str, subscriber_id: str) -> StreamState:
        state = self._require_stream(stream_id)
        now = time.monotonic()
        if state.controller_id != subscriber_id or state.control_expires_at <= now:
            raise RuntimeError("远程控制租约无效或已过期")
        return state

    def _control_is_idle(self, state: StreamState, now: float) -> bool:
        last_activity_at = state.last_control_activity_at or state.control_started_at
        return now - last_activity_at >= self.CONTROL_IDLE_TAKEOVER_SECONDS

    @staticmethod
    def _validate_claims(state: StreamState, claims: dict) -> None:
        for key in ("stream_id", "user_id", "executor_username", "connection_id", "execution_type", "execution_id"):
            if str(state.claims.get(key)) != str(claims.get(key)):
                raise RuntimeError("直播会话令牌与当前会话不匹配")

    def _check_control_rate(self, subscriber: SubscriberConnection) -> None:
        now = time.monotonic()
        while subscriber.control_events and now - subscriber.control_events[0] >= 1:
            subscriber.control_events.popleft()
        if len(subscriber.control_events) >= self.CONTROL_EVENTS_PER_SECOND:
            raise RuntimeError("远程控制事件频率过高")
        subscriber.control_events.append(now)

    async def _control_event_timeout(
            self,
            stream_id: str,
            subscriber_id: str,
            sequence: int,
            timeout_seconds: float,
    ) -> None:
        await asyncio.sleep(timeout_seconds)
        consumer = None
        event_type = ""
        async with self._lock:
            state = self._streams.get(stream_id)
            subscriber = state.subscribers.get(subscriber_id) if state else None
            if subscriber is None or subscriber.pending_control_sequence != sequence:
                return
            consumer = subscriber.consumer
            event_type = subscriber.pending_control_event_type
            self._clear_pending_control(subscriber, cancel_timeout=False)
            self._control_events_rejected += 1
        await consumer.send_json(
            {
                "type": LiveStreamEvent.CONTROL_ACK.value,
                "sequence": sequence,
                "success": False,
                "message": f"实时控制执行超时，操作已放弃：{event_type}",
            }
        )

    def _control_timeout_seconds(self, event_type: str) -> float:
        if event_type in self.LONG_RUNNING_CONTROL_EVENTS:
            return self.CONTROL_COMMAND_TIMEOUT_SECONDS
        return self.CONTROL_EVENT_TIMEOUT_SECONDS

    @staticmethod
    def _clear_pending_control(
            subscriber: SubscriberConnection,
            *,
            cancel_timeout: bool = True,
    ) -> None:
        timeout_task = subscriber.pending_control_timeout_task
        subscriber.pending_control_sequence = 0
        subscriber.pending_control_event_type = ""
        subscriber.pending_control_started_at = 0
        subscriber.pending_control_timeout_task = None
        if cancel_timeout and timeout_task and timeout_task is not asyncio.current_task():
            timeout_task.cancel()

    @staticmethod
    async def _queue_stop_command(state: StreamState, reason: str) -> None:
        command = SocketEnvelopeContract(
            code=200,
            msg="停止UI浏览器实时画面",
            user=state.claims["executor_username"],
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=LiveStreamCommand.STOP.value,
                func_args={"stream_id": state.stream_id, "reason": reason},
            ),
        )
        await database_sync_to_async(SocketMessageService.send_socket_data)(
            command,
            message_key=f"live-stream:stop:{state.stream_id}",
            ttl_seconds=REALTIME_COMMAND_TTL_SECONDS,
            created_by_service="realtime-service",
        )
