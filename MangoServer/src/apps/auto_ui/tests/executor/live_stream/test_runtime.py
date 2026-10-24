import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock, patch

from django.core import signing
from uvicorn.protocols.utils import ClientDisconnected

from src.apps.auto_ui.enums.live_stream import (
    LiveStreamRole,
)
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.live_stream.constants import REALTIME_COMMAND_TTL_SECONDS
from src.apps.auto_ui.services.live_stream.token_service import LiveStreamTokenService
from src.apps.auto_ui.services.live_stream.workspace_service import (
    LiveWorkspaceRecord,
    LiveWorkspaceService,
)
from src.apps.auto_ui.services.test_case.test_case import TestCase as UiTestCase
from src.apps.system.enums import ClientTypeEnum, SocketEnum
from src.processes.realtime.asgi import application as realtime_application
from src.processes.realtime.consumer import RealtimeConsumer
from src.processes.realtime.live_stream.registry import LiveStreamRegistry
from src.processes.realtime.registry import LocalConnection, LocalConnectionRegistry


class FakeConsumer:
    def __init__(self):
        self.json_messages = []
        self.binary_messages = []
        self.closed = False

    async def send_json(self, payload):
        self.json_messages.append(payload)

    async def send(self, *, bytes_data=None, **kwargs):
        if bytes_data is not None:
            self.binary_messages.append(bytes_data)

    async def close(self, code=None):
        self.closed = True


def stream_claims():
    return {
        "stream_id": "stream-1",
        "user_id": 1,
        "executor_username": "admin",
        "connection_id": "actuator-connection",
        "execution_type": "ui_case",
        "execution_id": "12",
    }


class LiveStreamTokenTest(TestCase):
    def test_token_role_is_strict(self):
        token = LiveStreamTokenService.issue(stream_claims(), LiveStreamRole.READY)
        claims = LiveStreamTokenService.verify(token, LiveStreamRole.READY)
        self.assertEqual(claims["stream_id"], "stream-1")
        self.assertEqual(claims["protocol_version"], 1)
        self.assertEqual(claims["permissions"], ["start"])
        self.assertGreater(claims["exp"], claims["issued_at"])
        self.assertTrue(claims["token_id"])
        self.assertTrue(claims["nonce"])
        with self.assertRaises(signing.BadSignature):
            LiveStreamTokenService.verify(token, LiveStreamRole.PUBLISHER)


class LiveWorkspaceStepDebugTest(TestCase):
    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace"
    )
    def test_page_step_debug_targets_workspace_executor(self, get_workspace):
        get_workspace.return_value = SimpleNamespace(
            username="maopeng",
            executor_username="open",
            workspace_type="page_step_workspace",
            resource_id=7,
        )
        test_case = UiTestCase(1, "maopeng", 1, is_send=True)

        test_case._TestCase__bind_live_workspace(7, "workspace-1")

        self.assertEqual(test_case.actuator_user, "open")
        self.assertTrue(test_case.actuator_user_explicit)

    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace"
    )
    def test_page_step_debug_rejects_workspace_for_another_step(self, get_workspace):
        get_workspace.return_value = SimpleNamespace(
            username="maopeng",
            executor_username="open",
            workspace_type="page_step_workspace",
            resource_id=8,
        )
        test_case = UiTestCase(1, "maopeng", 1, is_send=True)

        with self.assertRaises(AutoUiError):
            test_case._TestCase__bind_live_workspace(7, "workspace-1")


class LiveWorkspaceCloseTest(TestCase):
    def setUp(self):
        LiveWorkspaceService._workspace_by_id.clear()
        LiveWorkspaceService._workspace_by_key.clear()

    def tearDown(self):
        LiveWorkspaceService._workspace_by_id.clear()
        LiveWorkspaceService._workspace_by_key.clear()

    @patch.object(LiveWorkspaceService, "_send_command")
    def test_close_missing_workspace_is_idempotent(self, send_command):
        result = LiveWorkspaceService.close_workspace(
            {"username": "maopeng"},
            "missing-workspace",
            force=True,
        )

        self.assertEqual(result["status"], "closed")
        send_command.assert_not_called()

    @patch.object(LiveWorkspaceService, "_send_command", side_effect=RuntimeError("offline"))
    def test_force_close_cleans_workspace_when_executor_is_offline(self, send_command):
        record = LiveWorkspaceRecord(
            workspace_id="workspace-1",
            workspace_type="page_step_workspace",
            resource_id=7,
            test_env=1,
            username="maopeng",
            executor_username="open",
            connection_id="connection-1",
        )
        LiveWorkspaceService._workspace_by_id[record.workspace_id] = record
        LiveWorkspaceService._workspace_by_key[
            LiveWorkspaceService._workspace_key(
                record.username,
                record.test_env,
                record.executor_username,
                record.workspace_type,
                record.resource_id,
            )
        ] = record

        result = LiveWorkspaceService.close_workspace(
            {"username": "maopeng"},
            record.workspace_id,
            force=True,
        )

        self.assertEqual(result["status"], "closed")
        self.assertNotIn(record.workspace_id, LiveWorkspaceService._workspace_by_id)
        send_command.assert_called_once()

    def test_workspace_ready_status_can_be_queried_after_websocket_notice(self):
        record = LiveWorkspaceRecord(
            workspace_id="workspace-ready",
            workspace_type="page_step_workspace",
            resource_id=7,
            test_env=1,
            username="maopeng",
            executor_username="maopeng",
            connection_id="connection-1",
        )
        LiveWorkspaceService._save_record(record)

        updated = LiveWorkspaceService.update_workspace_status(
            record.workspace_id,
            "ready",
        )
        result = LiveWorkspaceService.workspace_status(
            {"username": "maopeng"},
            record.workspace_id,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["message"], "")

    def test_workspace_status_rejects_other_user(self):
        record = LiveWorkspaceRecord(
            workspace_id="workspace-private",
            workspace_type="page_step_workspace",
            resource_id=7,
            test_env=1,
            username="maopeng",
            executor_username="maopeng",
            connection_id="connection-1",
        )
        LiveWorkspaceService._save_record(record)

        with self.assertRaises(AutoUiError):
            LiveWorkspaceService.workspace_status(
                {"username": "other-user"},
                record.workspace_id,
            )


class LiveWorkspaceCommandPolicyTest(TestCase):
    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.SocketConnectionService.require_actuator"
    )
    def test_workspace_start_is_short_lived_and_idempotent(
            self,
            require_actuator,
            send_socket_data,
    ):
        record = LiveWorkspaceRecord(
            workspace_id="workspace-1",
            workspace_type="page_step_workspace",
            resource_id=7,
            test_env=1,
            username="maopeng",
            executor_username="open",
            connection_id="connection-1",
        )

        LiveWorkspaceService._send_workspace_start(
            record.executor_username,
            record,
            {"send_user": record.username},
        )

        require_actuator.assert_called_once_with("open")
        kwargs = send_socket_data.call_args.kwargs
        self.assertTrue(
            kwargs["message_key"].startswith(
                "live-workspace:start:workspace-1:connection-1:"
            )
        )
        self.assertEqual(kwargs["ttl_seconds"], REALTIME_COMMAND_TTL_SECONDS)


class LocalConnectionRegistryTest(IsolatedAsyncioTestCase):
    async def test_actuator_connection_is_unique_but_web_tabs_are_not(self):
        registry = LocalConnectionRegistry()
        first = FakeConsumer()
        second = FakeConsumer()
        web_one = FakeConsumer()
        web_two = FakeConsumer()
        await registry.register(LocalConnection("a1", 1, "admin", ClientTypeEnum.ACTUATOR.value, first))
        replaced = await registry.register(
            LocalConnection("a2", 1, "admin", ClientTypeEnum.ACTUATOR.value, second)
        )
        await registry.register(LocalConnection("w1", 1, "admin", ClientTypeEnum.WEB.value, web_one))
        await registry.register(LocalConnection("w2", 1, "admin", ClientTypeEnum.WEB.value, web_two))
        self.assertEqual(replaced.connection_id, "a1")
        self.assertEqual((await registry.get_actuator(1)).connection_id, "a2")
        self.assertEqual(len(await registry.get_web_connections(1)), 2)
        dirty_connections = await registry.drain_dirty_last_seen()
        self.assertNotIn("a1", dirty_connections)


class RealtimeConsumerConnectionTest(IsolatedAsyncioTestCase):
    def _consumer(self, registry):
        consumer = RealtimeConsumer(registry=registry, service_instance="test-realtime")
        consumer.scope = {"path": SocketEnum.CLIENT_PATH.value}
        consumer._verify_user = AsyncMock(return_value=(1, "admin"))
        consumer.accept = AsyncMock()
        consumer._notify_web = AsyncMock()
        return consumer

    @patch(
        "src.processes.realtime.consumer.SocketConnectionService.disconnect",
        return_value=True,
    )
    @patch("src.processes.realtime.consumer.SocketConnectionService.register")
    async def test_closed_replaced_connection_does_not_abort_handshake(
            self,
            register,
            disconnect,
    ):
        registry = LocalConnectionRegistry()
        old_consumer = FakeConsumer()
        old_consumer.close = AsyncMock(side_effect=RuntimeError("already closed"))
        await registry.register(
            LocalConnection("old", 1, "admin", ClientTypeEnum.ACTUATOR.value, old_consumer)
        )
        register.return_value = SimpleNamespace(
            connection=SimpleNamespace(connection_id="new")
        )
        consumer = self._consumer(registry)
        consumer.send_json = AsyncMock()

        await consumer.connect()

        consumer.send_json.assert_awaited_once()
        self.assertEqual((await registry.get_actuator(1)).connection_id, "new")
        disconnect.assert_not_called()

    @patch(
        "src.processes.realtime.consumer.SocketConnectionService.disconnect",
        return_value=True,
    )
    @patch("src.processes.realtime.consumer.SocketConnectionService.register")
    async def test_handshake_failure_rolls_back_registered_connection(
            self,
            register,
            disconnect,
    ):
        registry = LocalConnectionRegistry()
        register.return_value = SimpleNamespace(
            connection=SimpleNamespace(connection_id="failed")
        )
        consumer = self._consumer(registry)
        consumer.send_json = AsyncMock(side_effect=RuntimeError("handshake failed"))

        with self.assertRaisesRegex(RuntimeError, "handshake failed"):
            await consumer.connect()

        self.assertIsNone(await registry.get_actuator(1))
        self.assertEqual(consumer.connection_id, "")
        disconnect.assert_called_once_with("failed")

    @patch(
        "src.common.decorators.system_error.areport_system_error",
        new_callable=AsyncMock,
    )
    @patch(
        "src.processes.realtime.consumer.SocketConnectionService.disconnect",
        return_value=True,
    )
    @patch("src.processes.realtime.consumer.SocketConnectionService.register")
    async def test_client_disconnect_during_handshake_is_cleaned_without_system_error(
            self,
            register,
            disconnect,
            report_system_error,
    ):
        registry = LocalConnectionRegistry()
        register.return_value = SimpleNamespace(
            connection=SimpleNamespace(connection_id="disconnected")
        )
        consumer = self._consumer(registry)
        consumer.send_json = AsyncMock(side_effect=ClientDisconnected())

        await consumer.connect()

        self.assertIsNone(await registry.get_actuator(1))
        self.assertEqual(consumer.connection_id, "")
        disconnect.assert_called_once_with("disconnected")
        report_system_error.assert_not_awaited()

    @patch(
        "src.common.decorators.system_error.areport_system_error",
        new_callable=AsyncMock,
    )
    @patch("src.processes.realtime.consumer.SocketConnectionService.register")
    async def test_duplicate_accept_state_continues_without_system_error(
            self,
            register,
            report_system_error,
    ):
        registry = LocalConnectionRegistry()
        register.return_value = SimpleNamespace(
            connection=SimpleNamespace(connection_id="accepted")
        )
        consumer = self._consumer(registry)
        consumer.accept = AsyncMock(
            side_effect=RuntimeError(
                "Expected ASGI message 'websocket.send' or 'websocket.close', "
                "but got 'websocket.accept'."
            )
        )
        consumer.send_json = AsyncMock()

        await consumer.connect()

        self.assertTrue(consumer.websocket_accepted)
        consumer.send_json.assert_awaited_once()
        self.assertEqual((await registry.get_actuator(1)).connection_id, "accepted")
        report_system_error.assert_not_awaited()

    @patch(
        "src.common.decorators.system_error.areport_system_error",
        new_callable=AsyncMock,
    )
    @patch("src.processes.realtime.consumer.SocketConnectionService.register")
    async def test_client_disconnect_during_accept_is_not_a_system_error(
            self,
            register,
            report_system_error,
    ):
        consumer = self._consumer(LocalConnectionRegistry())
        consumer.accept = AsyncMock(side_effect=ClientDisconnected())

        await consumer.connect()

        register.assert_not_called()
        report_system_error.assert_not_awaited()

    async def test_workspace_status_notice_is_persisted_and_relayed(self):
        registry = LocalConnectionRegistry()
        consumer = self._consumer(registry)
        consumer.connection_id = "actuator"
        consumer.reflection.server_data_received.send = Mock()
        consumer._relay = AsyncMock()

        await consumer.receive_json(
            {
                "code": 200,
                "msg": "UI实时工作区准备完成",
                "user": "admin",
                "is_notice": ClientTypeEnum.WEB.value,
                "data": {
                    "func_name": "u_live_workspace_status",
                    "func_args": {"workspace_id": "workspace-1", "status": "ready"},
                },
            }
        )

        consumer._relay.assert_awaited_once()
        consumer.reflection.server_data_received.send.assert_called_once()
        callback = consumer.reflection.server_data_received.send.call_args.kwargs["data"]
        self.assertEqual(callback.func_name, "u_live_workspace_status")

    async def test_executor_result_notice_is_reflected_and_relayed(self):
        registry = LocalConnectionRegistry()
        consumer = self._consumer(registry)
        consumer.connection_id = "actuator"
        consumer.reflection.server_data_received.send = Mock()
        consumer._relay = AsyncMock()

        await consumer.receive_json(
            {
                "message_id": "result-1",
                "code": 200,
                "msg": "UI步骤实时结果已更新",
                "user": "admin",
                "is_notice": ClientTypeEnum.WEB.value,
                "data": {
                    "func_name": "u_page_steps",
                    "func_args": {"id": 7, "status": 3, "is_final": False},
                },
            }
        )

        consumer._relay.assert_awaited_once()
        consumer.reflection.server_data_received.send.assert_called_once()
        reflected = consumer.reflection.server_data_received.send.call_args.kwargs["data"]
        self.assertEqual(reflected.func_name, "u_page_steps")
        self.assertEqual(reflected.message_id, "result-1")


class LiveStreamRegistryTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = LiveStreamRegistry()
        self.subscriber = FakeConsumer()
        self.publisher = FakeConsumer()
        self.subscriber_id, _ = await self.registry.register_subscriber(stream_claims(), self.subscriber)
        self.publisher_id = await self.registry.register_publisher(stream_claims(), self.publisher)

    async def asyncTearDown(self):
        await self.registry.close_all()

    async def test_frame_is_forwarded_and_control_is_leased(self):
        viewer_count = await self.registry.publish_frame("stream-1", self.publisher_id, b"jpeg-frame")
        await asyncio.sleep(0)
        self.assertEqual(viewer_count, 1)
        self.assertEqual(self.subscriber.binary_messages[-1], b"jpeg-frame")

        lease = await self.registry.acquire_control("stream-1", self.subscriber_id)
        self.assertEqual(lease["lease_seconds"], self.registry.CONTROL_LEASE_SECONDS)
        await self.registry.relay_control(
            "stream-1",
            self.subscriber_id,
            {"event_type": "mouse_click", "x": 0.5, "y": 0.5, "sequence": 1},
        )
        self.assertEqual(self.publisher.json_messages[-1]["type"], "control_event")
        with self.assertRaisesRegex(RuntimeError, "仍在处理中"):
            await self.registry.relay_control(
                "stream-1",
                self.subscriber_id,
                {"event_type": "mouse_click", "x": 0.5, "y": 0.5, "sequence": 2},
            )
        await self.registry.relay_publisher_status(
            "stream-1",
            self.publisher_id,
            {"type": "control_ack", "sequence": 1, "success": True},
        )
        self.assertEqual(self.subscriber.json_messages[-1]["sequence"], 1)
        await self.registry.relay_control(
            "stream-1",
            self.subscriber_id,
            {"event_type": "mouse_click", "x": 0.5, "y": 0.5, "sequence": 3},
        )
        stats = await self.registry.stats()
        self.assertEqual(stats["control_events_total"], 2)
        self.assertEqual(stats["control_events_rejected"], 1)

    async def test_invalid_control_event_is_rejected(self):
        await self.registry.acquire_control("stream-1", self.subscriber_id)
        with self.assertRaises(RuntimeError):
            await self.registry.relay_control(
                "stream-1",
                self.subscriber_id,
                {"event_type": "evaluate_javascript", "sequence": 1},
            )
        with self.assertRaises(RuntimeError):
            await self.registry.relay_control(
                "stream-1",
                self.subscriber_id,
                {"event_type": "mouse_move", "x": 2, "y": 0.5, "sequence": 2},
            )
        with self.assertRaises(RuntimeError):
            await self.registry.relay_control(
                "stream-1",
                self.subscriber_id,
                {"event_type": "text_input", "text": "x" * 2001, "sequence": 3},
            )
        stats = await self.registry.stats()
        self.assertEqual(stats["control_events_total"], 0)
        self.assertEqual(stats["control_events_rejected"], 3)

    async def test_control_timeout_is_reported_and_late_ack_is_dropped(self):
        await self.registry.acquire_control("stream-1", self.subscriber_id)
        self.registry.CONTROL_EVENT_TIMEOUT_SECONDS = 0.01
        await self.registry.relay_control(
            "stream-1",
            self.subscriber_id,
            {"event_type": "mouse_click", "x": 0.5, "y": 0.5, "sequence": 1},
        )

        await asyncio.sleep(0.02)

        timeout_message = self.subscriber.json_messages[-1]
        self.assertEqual(timeout_message["type"], "control_ack")
        self.assertFalse(timeout_message["success"])
        self.assertIn("超时", timeout_message["message"])
        message_count = len(self.subscriber.json_messages)
        await self.registry.relay_publisher_status(
            "stream-1",
            self.publisher_id,
            {"type": "control_ack", "sequence": 1, "success": True},
        )
        self.assertEqual(len(self.subscriber.json_messages), message_count)

    async def test_degraded_stream_drops_frames_and_expired_control_is_released(self):
        await self.registry.set_degraded(True)
        viewer_count = await self.registry.publish_frame("stream-1", self.publisher_id, b"jpeg-frame")
        self.assertEqual(viewer_count, 0)
        self.assertEqual(self.subscriber.binary_messages, [])

        await self.registry.set_degraded(False)
        await self.registry.acquire_control("stream-1", self.subscriber_id)
        state = self.registry._streams["stream-1"]
        state.control_expires_at = 0
        await self.registry.cleanup_expired()
        self.assertIsNone(state.controller_id)
        self.assertEqual(self.publisher.json_messages[-1]["type"], "control_stopped")
        self.assertEqual(self.publisher.json_messages[-1]["reason"], "lease_expired")

    async def test_publisher_disconnect_notifies_subscriber(self):
        await self.registry.remove_publisher("stream-1", self.publisher_id)
        message = self.subscriber.json_messages[-1]
        self.assertEqual(message["type"], "stream_status")
        self.assertEqual(message["data"]["status"], "disconnected")


class RealtimeHealthEndpointTest(IsolatedAsyncioTestCase):
    async def test_liveness_endpoint(self):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await realtime_application(
            {"type": "http", "path": "/health/live", "method": "GET"},
            receive,
            send,
        )
        self.assertEqual(messages[0]["status"], 200)
        self.assertTrue(messages[0]["headers"][0][1].startswith(b"application/json"))
        self.assertIn(b'realtime-service', messages[1]["body"])

    async def test_readiness_fails_before_lifespan_start(self):
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await realtime_application(
            {"type": "http", "path": "/health/ready", "method": "GET"},
            receive,
            send,
        )
        self.assertEqual(messages[0]["status"], 503)
