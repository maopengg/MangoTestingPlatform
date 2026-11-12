from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.auto_ui.api.views.ui_case import UiCaseViews
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.elements.element_service import PageElementService
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.execution.cases.test_case import TestCase
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ServerUiCommandEnum
from src.common.exceptions import ErrorDefinition


class UiExecutorDispatchTest(SimpleTestCase):
    def setUp(self):
        ExecutorSlotLeaseService.reset_for_tests()

    def tearDown(self):
        ExecutorSlotLeaseService.reset_for_tests()

    def _service(self, *, actuator_username="open"):
        return TestCase(
            user_id=1,
            username="maopeng",
            test_env=1,
            is_send=True,
            actuator_username=actuator_username,
        )

    @patch(
        "src.apps.auto_ui.api.views.ui_case.SocketConnectionService.require_actuator",
        side_effect=AutoUiError(ErrorDefinition(code=1028, message="执行器不在线")),
    )
    def test_explicit_executor_is_validated_before_case_execution(
            self,
            require_actuator,
    ):
        request = SimpleNamespace(
            query_params={"actuator_username": "selected-offline"},
            user={"username": "maopeng"},
        )

        with self.assertRaisesRegex(
                AutoUiError,
                '所选执行器【selected-offline】当前不可用',
        ):
            UiCaseViews._validated_actuator_username(request)

        require_actuator.assert_called_once_with("selected-offline")

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.UiCaseStepsDetailed.objects.filter"
    )
    def test_new_case_execution_resets_all_step_runtime_states(self, filter_mock):
        TestCase._reset_case_step_runtime_status(12)

        filter_mock.assert_called_once_with(case_id=12)
        filter_mock.return_value.update.assert_called_once_with(
            status=TaskEnum.STAY_BEGIN.value,
            error_message=None,
        )

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator"
    )
    def test_page_step_debug_is_sent_to_selected_executor(
            self,
            require_actuator,
            send_socket_data,
    ):
        service = self._service()

        service._TestCase__socket_send(
            {"id": 8, "name": "Mango Mock 按钮与自愈调试"},
            ServerUiCommandEnum.PAGE_STEPS.value,
        )

        require_actuator.assert_called_once_with("open")
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "open")
        self.assertEqual(command.is_notice, ClientTypeEnum.ACTUATOR.value)
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.PAGE_STEPS.value)
        self.assertEqual(command.data.func_args["id"], 8)
        self.assertEqual(send_socket_data.call_args.kwargs["created_by"], 1)

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.ExecutorSlotLeaseService.set_running"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator"
    )
    def test_open_target_page_reuses_idle_slot_without_marking_task_running(
            self,
            require_actuator,
            send_socket_data,
            set_running,
    ):
        service = self._service()

        service._TestCase__socket_send(
            {"id": 8, "name": "目标页面"},
            ServerUiCommandEnum.OPEN_TARGET_PAGE.value,
            mark_running=False,
        )

        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.OPEN_TARGET_PAGE.value)
        self.assertTrue(command.data.func_args["slot_id"])
        set_running.assert_not_called()

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator"
    )
    def test_element_check_is_sent_to_selected_executor(
            self,
            require_actuator,
            send_socket_data,
    ):
        service = self._service()

        service._TestCase__socket_send(
            {
                "check_id": "check-mango-mock",
                "element_list": [{"name": "单击"}],
            },
            ServerUiCommandEnum.ELEMENT_CHECK.value,
        )

        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "open")
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.ELEMENT_CHECK.value)
        self.assertEqual(command.data.func_args["check_id"], "check-mango-mock")

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator"
    )
    def test_case_execution_is_sent_to_selected_executor(
            self,
            require_actuator,
            send_socket_data,
    ):
        service = self._service()

        service._TestCase__socket_send(
            {"id": 12, "name": "Mango Mock UI 执行与直播"},
            ServerUiCommandEnum.CASE_BATCH.value,
            is_open=True,
        )

        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "open")
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.CASE_BATCH.value)
        self.assertEqual(command.data.func_args["id"], 12)

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.list_open_actuator_usernames",
        return_value=["shared-open"],
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator",
    )
    def test_case_execution_can_fallback_to_open_executor(
            self,
            require_actuator,
            list_open_actuators,
            send_socket_data,
    ):
        service = self._service(actuator_username=None)
        service.actuator_user_explicit = False
        require_actuator.side_effect = [
            AutoUiError(ErrorDefinition(code=1028, message="执行器不在线")),
            SimpleNamespace(
                connection_id="shared-connection",
                user=SimpleNamespace(username="shared-open"),
            ),
        ]

        service._TestCase__socket_send(
            {"id": 12},
            ServerUiCommandEnum.CASE_BATCH.value,
            is_open=True,
        )

        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.user, "shared-open")

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.list_open_actuator_usernames",
        return_value=["shared-open"],
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator",
    )
    def test_case_execution_falls_back_when_self_disconnects_during_dispatch(
            self,
            require_actuator,
            list_open_actuators,
            send_socket_data,
    ):
        service = self._service(actuator_username=None)
        service.actuator_user_explicit = False
        require_actuator.side_effect = [
            SimpleNamespace(connection_id="self-connection"),
            SimpleNamespace(
                connection_id="shared-connection",
                user=SimpleNamespace(username="shared-open"),
            ),
        ]
        send_socket_data.side_effect = [
            SimpleNamespace(status="failed"),
            SimpleNamespace(status="pending"),
        ]

        service._TestCase__socket_send(
            {"id": 12},
            ServerUiCommandEnum.CASE_BATCH.value,
            is_open=True,
        )

        self.assertEqual(send_socket_data.call_count, 2)
        self.assertEqual(send_socket_data.call_args.args[0].user, "shared-open")
        for call in send_socket_data.call_args_list:
            self.assertEqual(call.kwargs["ttl_seconds"], 0)

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.list_open_actuator_usernames"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator",
        side_effect=AutoUiError(ErrorDefinition(code=1028, message="执行器不在线")),
    )
    def test_explicit_executor_failure_is_reported_without_fallback(
            self,
            require_actuator,
            list_open_actuators,
            send_socket_data,
    ):
        service = self._service(actuator_username="open")

        with self.assertRaisesRegex(AutoUiError, '所选执行器【open】当前不可用'):
            service._TestCase__socket_send(
                {"id": 12},
                ServerUiCommandEnum.CASE_BATCH.value,
                is_open=True,
            )

        list_open_actuators.assert_not_called()
        send_socket_data.assert_called_once()
        self.assertEqual(
            send_socket_data.call_args.kwargs["executor_mode"],
            "specified",
        )
        self.assertEqual(send_socket_data.call_args.kwargs["ttl_seconds"], 0)

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.list_open_actuator_usernames",
        return_value=[],
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator",
        side_effect=AutoUiError(ErrorDefinition(code=1028, message="执行器不在线")),
    )
    def test_case_execution_without_self_or_open_executor_fails_immediately(
            self,
            require_actuator,
            list_open_actuators,
            send_socket_data,
    ):
        service = self._service(actuator_username=None)
        service.actuator_user_explicit = False

        with self.assertRaisesRegex(AutoUiError, '当前没有可用的执行器'):
            service._TestCase__socket_send(
                {"id": 12},
                ServerUiCommandEnum.CASE_BATCH.value,
                is_open=True,
            )

        list_open_actuators.assert_called_once_with()
        send_socket_data.assert_called_once()
        self.assertEqual(send_socket_data.call_args.kwargs["executor_mode"], "self")
        self.assertEqual(send_socket_data.call_args.kwargs["ttl_seconds"], 0)

    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
    )
    @patch(
        "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator",
        side_effect=AutoUiError(ErrorDefinition(code=1028, message="执行器不在线")),
    )
    def test_offline_interactive_task_is_created_fail_fast(
            self,
            require_actuator,
            send_socket_data,
    ):
        service = self._service(actuator_username=None)

        with self.assertRaisesRegex(AutoUiError, '当前没有可用的执行器'):
            service._TestCase__socket_send(
                {"id": 8},
                ServerUiCommandEnum.PAGE_STEPS.value,
            )

        self.assertEqual(send_socket_data.call_args.kwargs["executor_mode"], "self")
        self.assertEqual(send_socket_data.call_args.kwargs["ttl_seconds"], 0)

    def test_is_send_false_never_contacts_executor(self):
        service = TestCase(
            user_id=1,
            username="maopeng",
            test_env=1,
            is_send=False,
        )

        with patch(
                "src.apps.auto_ui.services.execution.cases.test_case.SocketConnectionService.require_actuator"
        ) as require_actuator, patch(
            "src.apps.auto_ui.services.execution.cases.test_case.SocketMessageService.send_socket_data"
        ) as send_socket_data:
            service._TestCase__socket_send(
                SimpleNamespace(id=8),
                ServerUiCommandEnum.PAGE_STEPS.value,
            )

        require_actuator.assert_not_called()
        send_socket_data.assert_not_called()

    @patch("src.apps.system.services.socket_link.message_service.SocketMessageService.send_socket_data")
    @patch("src.apps.auto_ui.services.live_stream.workspace_service.LiveWorkspaceService.get_workspace")
    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.filter")
    def test_page_scan_is_created_as_workspace_executor_task(
            self,
            page_filter,
            get_workspace,
            send_socket_data,
    ):
        page_filter.return_value.exists.return_value = True
        get_workspace.return_value = SimpleNamespace(
            workspace_id="workspace-1",
            workspace_type="element_workspace",
            username="maopeng",
            user_id=1,
            executor_username="open",
        )
        send_socket_data.return_value = SimpleNamespace(id=81, status="pending")

        result = PageElementService.scan_page_elements(
            page_id=12,
            user_id=1,
            username="maopeng",
            workspace_id="workspace-1",
            scan_mode="deep",
        )

        self.assertEqual(result["task_id"], 81)
        command = send_socket_data.call_args.args[0]
        self.assertEqual(command.data.func_name, ServerUiCommandEnum.PAGE_SCAN.value)
        self.assertEqual(command.data.func_args["mode"], "deep")
        self.assertEqual(send_socket_data.call_args.kwargs["executor_mode"], "workspace")
        self.assertEqual(send_socket_data.call_args.kwargs["ttl_seconds"], 0)

    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.filter")
    def test_page_scan_rejects_missing_page(self, page_filter):
        page_filter.return_value.exists.return_value = False

        with self.assertRaisesRegex(AutoUiError, "待扫描的页面不存在"):
            PageElementService.scan_page_elements(
                page_id=999,
                user_id=1,
                username="maopeng",
                workspace_id="workspace-1",
                scan_mode="quick",
            )

    @patch("src.apps.auto_ui.services.elements.element_service.Page.objects.filter")
    def test_page_scan_rejects_unknown_mode(self, page_filter):
        page_filter.return_value.exists.return_value = True

        with self.assertRaisesRegex(AutoUiError, "页面元素扫描模式无效"):
            PageElementService.scan_page_elements(
                page_id=12,
                user_id=1,
                username="maopeng",
                workspace_id="workspace-1",
                scan_mode="unknown",
            )
