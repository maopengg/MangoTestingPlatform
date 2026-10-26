from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.api.views.socket_api import SocketApiViews
from src.apps.system.enums import ServerUiCommandEnum


class UiBrowserSessionExecutorTest(SimpleTestCase):
    @patch(
        "src.apps.system.api.views.socket_api.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.system.api.views.socket_api.SocketConnectionService.require_actuator"
    )
    def test_new_browser_object_is_dispatched_to_current_user_executor(
            self,
            require_actuator,
            send_socket_data,
    ):
        request = SimpleNamespace(
            query_params={},
            user={"id": 4, "username": "maopeng"},
        )

        response = SocketApiViews().get_new_browser_obj(request)

        self.assertEqual(response.data["code"], 200)
        require_actuator.assert_called_once_with("maopeng")
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "maopeng")
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.NEW_PAGE_OBJ.value)

    @patch(
        "src.apps.system.api.views.socket_api.UserCacheService.selected_environment",
        return_value=1,
    )
    @patch(
        "src.apps.system.api.views.socket_api.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.system.api.views.socket_api.SocketConnectionService.require_actuator"
    )
    @patch(
        "src.apps.system.api.views.socket_api.TestObject.objects.filter"
    )
    @patch(
        "src.apps.system.api.views.socket_api.ProjectProduct.objects.all"
    )
    @patch(
        "src.apps.system.api.views.socket_api.User.objects.get"
    )
    def test_recording_browser_receives_allowed_host_list(
            self,
            get_user,
            all_products,
            filter_test_objects,
            require_actuator,
            send_socket_data,
            selected_environment,
    ):
        get_user.return_value = SimpleNamespace(selected_environment=1)
        product_queryset = SimpleNamespace(
            values_list=lambda *args, **kwargs: [7],
        )
        all_products.return_value = product_queryset
        filter_test_objects.return_value = SimpleNamespace(
            values=lambda *args: [{
                "value": "http://mock.example.com:8003/#components",
                "project_product_id": 7,
            }],
        )
        request = SimpleNamespace(
            query_params={"is_recording": "1"},
            user={"id": 4, "username": "maopeng"},
            headers={},
        )

        response = SocketApiViews().get_new_browser_obj(request)

        self.assertEqual(response.data["code"], 200)
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.RECORDING.value)
        self.assertEqual(
            command.data.func_args.url_list[0]["value"],
            "http://mock.example.com:8003/#components",
        )
