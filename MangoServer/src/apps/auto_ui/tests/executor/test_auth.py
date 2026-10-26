from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.api.views.ui_auth_config import UiAuthConfigViews
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ServerUiCommandEnum


class UiAuthExecutorDispatchTest(SimpleTestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            data={"id": 3},
            user={"id": 4, "username": "maopeng"},
        )
        self.config = SimpleNamespace(
            id=3,
            auto_auth_config={
                "url": "http://43.142.161.61:8003/#components",
                "cookie_domains": ["43.142.161.61"],
                "local_storage_keys": ["mango-token"],
                "session_storage_keys": ["mango-run"],
                "headers": {"X-Mango-Probe": "1"},
                "timeout": 120,
            },
        )

    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.UiAuthManager.resolve_origin",
        return_value="http://43.142.161.61:8003",
    )
    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.UiAuthManager.resolve_test_object_url",
        return_value="http://43.142.161.61:8003/#components",
    )
    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.UiAuthConfig.objects.get"
    )
    def test_auto_auth_start_sends_complete_configuration(
            self,
            get_config,
            send_socket_data,
            resolve_url,
            resolve_origin,
    ):
        get_config.return_value = self.config
        send_socket_data.return_value = SimpleNamespace(id=31, status="waiting_executor")

        response = UiAuthConfigViews().auto_start(self.request)

        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["task_id"], 31)
        self.assertEqual(response.data["data"]["task_status"], "waiting_executor")
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "maopeng")
        self.assertEqual(command.is_notice, ClientTypeEnum.ACTUATOR.value)
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.AUTH_AUTO.value)
        self.assertEqual(
            command.data.func_args["url"],
            "http://43.142.161.61:8003/#components",
        )
        self.assertEqual(command.data.func_args["timeout"], 120)
        self.assertEqual(command.data.func_args["send_user"], "maopeng")

    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.UiAuthManager.resolve_origin",
        return_value="http://43.142.161.61:8003",
    )
    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.api.views.ui_auth_config.UiAuthConfig.objects.get"
    )
    def test_auto_auth_capture_targets_same_user_executor(
            self,
            get_config,
            send_socket_data,
            resolve_origin,
    ):
        get_config.return_value = self.config
        send_socket_data.return_value = SimpleNamespace(id=32, status="pending")

        response = UiAuthConfigViews().auto_capture(self.request)

        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["task_id"], 32)
        self.assertEqual(response.data["data"]["task_status"], "pending")
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.AUTH_AUTO_CAPTURE.value)
        self.assertEqual(
            command.data.func_args["origin"],
            "http://43.142.161.61:8003",
        )
        self.assertEqual(command.data.func_args["send_user"], "maopeng")
