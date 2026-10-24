import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, mock

from src.network.web_socket.websocket_client import ConnectionState, WebSocketClient


class WebSocketHeartbeatTest(IsolatedAsyncioTestCase):
    async def test_stale_server_registration_closes_authenticated_socket(self):
        websocket = SimpleNamespace(
            closed=False,
            close=mock.AsyncMock(),
        )
        original_state = WebSocketClient._connection_state
        original_websocket = WebSocketClient.websocket
        WebSocketClient._connection_state = ConnectionState.AUTHENTICATED
        WebSocketClient.websocket = websocket

        try:
            with mock.patch(
                "src.network.web_socket.websocket_client.send_global_msg",
            ) as send_global_msg:
                reconnected = await WebSocketClient.reconnect_if_authenticated("登记不存在")

            self.assertTrue(reconnected)
            self.assertEqual(WebSocketClient._connection_state, ConnectionState.DISCONNECTED)
            websocket.close.assert_awaited_once_with(
                code=1012,
                reason="server registration lost",
            )
            send_global_msg.assert_called_once()
        finally:
            WebSocketClient._connection_state = original_state
            WebSocketClient.websocket = original_websocket

    async def test_stale_registration_does_not_interrupt_connecting_socket(self):
        websocket = SimpleNamespace(
            closed=False,
            close=mock.AsyncMock(),
        )
        original_state = WebSocketClient._connection_state
        original_websocket = WebSocketClient.websocket
        WebSocketClient._connection_state = ConnectionState.CONNECTING
        WebSocketClient.websocket = websocket

        try:
            reconnected = await WebSocketClient.reconnect_if_authenticated("启动竞态")

            self.assertFalse(reconnected)
            websocket.close.assert_not_awaited()
        finally:
            WebSocketClient._connection_state = original_state
            WebSocketClient.websocket = original_websocket

    async def test_heartbeat_sends_application_message_to_refresh_server_last_seen(self):
        pong_waiter = asyncio.get_running_loop().create_future()
        pong_waiter.set_result(None)
        websocket = SimpleNamespace(
            ping=mock.AsyncMock(return_value=pong_waiter),
        )

        original_running = WebSocketClient.running
        original_websocket = WebSocketClient.websocket
        WebSocketClient.running = True
        WebSocketClient.websocket = websocket

        async def stop_after_first_heartbeat(_seconds):
            WebSocketClient.running = False

        try:
            with mock.patch.object(
                WebSocketClient,
                "_send_direct",
                new=mock.AsyncMock(),
            ) as send_direct, mock.patch(
                "src.network.web_socket.websocket_client.asyncio.sleep",
                side_effect=stop_after_first_heartbeat,
            ):
                await WebSocketClient._heartbeat()

            websocket.ping.assert_awaited_once()
            send_direct.assert_awaited_once_with("执行器心跳", log_success=False)
        finally:
            WebSocketClient.running = original_running
            WebSocketClient.websocket = original_websocket
