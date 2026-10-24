from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.interfaces.mcp.tools.ui.element import register_element_tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class UiElementMcpToolTests(SimpleTestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        register_element_tools(self.registry)

    @patch(
        "src.interfaces.mcp.tools.ui.element.current_user",
        return_value=SimpleNamespace(id=4, username="mcp-smoke"),
    )
    @patch("src.interfaces.mcp.tools.ui.element.PageElementService.check_element")
    def test_ui_element_uses_current_check_service(self, check_element, _current_user):
        check_element.return_value = {"check_id": "check-1"}

        result = self.registry.tools["test_ui_element"](
            {
                "element_id": 12,
                "workspace_id": "workspace-1",
                "check_mode": "deep",
                "runtime_variables": {"tenant": "test"},
            },
            test_env_id=3,
        )

        self.assertTrue(result["success"])
        check_element.assert_called_once_with(
            12,
            4,
            "mcp-smoke",
            3,
            "workspace-1",
            "deep",
            {"tenant": "test"},
        )

    @patch(
        "src.interfaces.mcp.tools.ui.element.current_user",
        return_value=SimpleNamespace(id=4, username="mcp-smoke"),
    )
    def test_ui_element_missing_id_returns_expected_ui_error(self, _current_user):
        result = self.registry.tools["test_ui_element"]({})

        self.assertFalse(result["success"])
        self.assertNotEqual(result["error_code"], "MCP_TOOL_EXCEPTION")
