from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.enums.live_stream import (
    LiveStreamCommand,
    LiveStreamExecutionType,
)
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.live_stream.constants import REALTIME_COMMAND_TTL_SECONDS
from src.apps.auto_ui.services.live_stream.session_service import LiveStreamSessionService


class UiCaseLiveSessionTest(SimpleTestCase):
    def setUp(self):
        ExecutorSlotLeaseService.reset_for_tests()
        self.user = {"id": 4, "username": "maopeng"}
        self.claims = {
            "stream_id": "stream-case-12",
            "user_id": 4,
            "executor_username": "open",
            "connection_id": "actuator-connection",
            "execution_type": LiveStreamExecutionType.UI_CASE.value,
            "execution_id": "12",
            "resource_id": "12",
            "read_only": False,
            "slot_id": "slot-4",
            "idle_deadline": 1300,
            "idle_timeout_seconds": 300,
        }

    def tearDown(self):
        ExecutorSlotLeaseService.reset_for_tests()

    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamSessionStore.create"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.SocketConnectionService.require_actuator"
    )
    @patch.object(
        LiveStreamSessionService,
        "_resolve_executor_username",
        return_value="open",
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamPermissionService.validate_execution"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.uuid.uuid4",
        return_value="stream-case-12",
    )
    def test_case_live_session_is_created_for_selected_executor(
            self,
            uuid4,
            validate_execution,
            resolve_executor,
            require_actuator,
            create_session,
    ):
        require_actuator.return_value = SimpleNamespace(
            connection_id="actuator-connection",
            user=SimpleNamespace(username="open"),
        )

        result = LiveStreamSessionService.create_session(
            self.user,
            LiveStreamExecutionType.UI_CASE.value,
            "12",
            resource_id="12",
            actuator_username="open",
        )

        self.assertEqual(result["stream_id"], "stream-case-12")
        validate_execution.assert_called_once_with(
            LiveStreamExecutionType.UI_CASE.value,
            "12",
        )
        create_session.assert_called_once()
        claims = create_session.call_args.args[0]
        self.assertEqual(claims["executor_username"], "open")
        self.assertEqual(claims["execution_type"], "ui_case")
        self.assertEqual(claims["execution_id"], "12")
        self.assertEqual(claims["slot_id"], "stream-case-12")

    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.SocketConnectionService.require_actuator"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamTokenService.issue",
        return_value="publish-token",
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamTokenService.verify"
    )
    def test_case_live_start_enqueues_one_short_lived_stream_command(
            self,
            verify_token,
            issue_token,
            require_actuator,
            send_socket_data,
    ):
        verify_token.return_value = self.claims
        require_actuator.return_value = SimpleNamespace(
            connection_id="actuator-connection"
        )

        result = LiveStreamSessionService.start_session(
            self.user,
            "stream-case-12",
            "ready-token",
        )

        self.assertEqual(result["status"], "waiting_publisher")
        send_socket_data.assert_called_once()
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "open")
        self.assertEqual(command.data.func_name, LiveStreamCommand.START.value)
        self.assertEqual(command.data.func_args["execution_type"], "ui_case")
        self.assertEqual(command.data.func_args["execution_id"], "12")
        self.assertEqual(command.data.func_args["send_user"], "maopeng")
        self.assertEqual(
            send_socket_data.call_args.kwargs["message_key"],
            "live-stream:start:stream-case-12",
        )
        self.assertEqual(
            send_socket_data.call_args.kwargs["ttl_seconds"],
            REALTIME_COMMAND_TTL_SECONDS,
        )

    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamSessionStore.close"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.LiveStreamSessionStore.get_claims"
    )
    @patch(
        "src.apps.auto_ui.services.live_stream.session_service.SocketMessageService.send_socket_data"
    )
    def test_case_live_close_stops_stream_and_cleans_session(
            self,
            send_socket_data,
            get_claims,
            close_session,
    ):
        get_claims.return_value = self.claims

        result = LiveStreamSessionService.close_session(
            self.user,
            "stream-case-12",
        )

        self.assertEqual(result["status"], "closed")
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.data.func_name, LiveStreamCommand.STOP.value)
        close_session.assert_called_once_with("stream-case-12")

    def test_another_user_cannot_start_or_close_case_live_session(self):
        with self.assertRaisesRegex(AutoUiError, "无权访问"):
            LiveStreamSessionService._validate_user_stream(
                {"id": 5, "username": "viewer"},
                "stream-case-12",
                self.claims,
            )


class UiPageStepLiveSessionTest(SimpleTestCase):
    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace"
    )
    def test_page_step_live_uses_workspace_executor(self, get_workspace):
        get_workspace.return_value = SimpleNamespace(
            username="maopeng",
            executor_username="open",
        )

        executor = LiveStreamSessionService._resolve_executor_username(
            {"id": 4, "username": "maopeng"},
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
            "workspace-8",
        )

        self.assertEqual(executor, "open")

    @patch(
        "src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace",
        return_value=None,
    )
    def test_page_step_live_rejects_expired_workspace(self, get_workspace):
        with self.assertRaisesRegex(AutoUiError, "实时工作区不存在或已过期"):
            LiveStreamSessionService._resolve_executor_username(
                {"id": 4, "username": "maopeng"},
                LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value,
                "workspace-expired",
            )
