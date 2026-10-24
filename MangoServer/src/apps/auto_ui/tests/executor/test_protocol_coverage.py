from django.test import SimpleTestCase

from src.apps.system.enums import ServerUiCommandEnum


class UiExecutorProtocolCoverageTest(SimpleTestCase):
    """防止新增 UI 执行器命令后没有对应分类测试。"""

    COVERED_EXECUTOR_COMMANDS = {
        ServerUiCommandEnum.PAGE_STEPS.value,
        ServerUiCommandEnum.OPEN_TARGET_PAGE.value,
        ServerUiCommandEnum.ELEMENT_CHECK.value,
        ServerUiCommandEnum.CASE_BATCH.value,
        ServerUiCommandEnum.AUTH_AUTO.value,
        ServerUiCommandEnum.AUTH_AUTO_CAPTURE.value,
        ServerUiCommandEnum.NEW_PAGE_OBJ.value,
        ServerUiCommandEnum.RECORDING.value,
        ServerUiCommandEnum.LIVE_STREAM_START.value,
        ServerUiCommandEnum.LIVE_STREAM_STOP.value,
        ServerUiCommandEnum.LIVE_WORKSPACE_START.value,
        ServerUiCommandEnum.LIVE_WORKSPACE_STOP.value,
    }

    def test_all_auto_ui_executor_commands_are_classified(self):
        expected = {
            "u_page_step",
            "u_open_target_page",
            "u_element_check",
            "u_case",
            "u_auth_auto",
            "u_auth_auto_capture",
            "u_page_new_obj",
            "u_recording",
            "u_live_stream_start",
            "u_live_stream_stop",
            "u_live_workspace_start",
            "u_live_workspace_stop",
        }

        self.assertEqual(self.COVERED_EXECUTOR_COMMANDS, expected)
