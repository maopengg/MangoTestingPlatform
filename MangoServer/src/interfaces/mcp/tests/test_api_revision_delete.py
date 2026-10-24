from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from src.interfaces.mcp.tools.api.delete import register_delete_tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class ApiRevisionDeleteToolTests(SimpleTestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        register_delete_tools(self.registry)

    def test_revision_delete_tools_are_registered(self):
        self.assertIn("preview_delete_api_info_revision_impact", self.registry.tools)
        self.assertIn("delete_api_info_revision", self.registry.tools)
        self.assertIn("preview_delete_api_case_revision_impact", self.registry.tools)
        self.assertIn("delete_api_case_revision", self.registry.tools)

    @patch(
        "src.interfaces.mcp.tools.api.delete.ApiInfoRevisionService.delete_unpublished_revision",
        return_value={"revision_id": 12, "revision_no": 4},
    )
    @patch(
        "src.interfaces.mcp.tools.api.delete._api_info_revision_delete_impact",
        return_value={"can_delete": True},
    )
    @patch(
        "src.interfaces.mcp.tools.api.delete.validate_dangerous_action_confirmation",
        return_value=None,
    )
    @patch("src.interfaces.mcp.tools.api.delete.transaction.atomic", return_value=nullcontext())
    def test_delete_api_info_revision_uses_version_service(
            self,
            _atomic,
            _validate,
            _impact,
            delete_revision,
    ):
        result = self.registry.tools["delete_api_info_revision"](5, 12)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"], {"api_info_id": 5, "revision_id": 12, "revision_no": 4})
        delete_revision.assert_called_once_with(5, 12)

    @patch(
        "src.interfaces.mcp.tools.api.delete.ApiCaseRevisionService.delete_unpublished_revision",
        return_value={"revision_id": 23, "revision_no": 6},
    )
    @patch(
        "src.interfaces.mcp.tools.api.delete._api_case_revision_delete_impact",
        return_value={"can_delete": True},
    )
    @patch(
        "src.interfaces.mcp.tools.api.delete.validate_dangerous_action_confirmation",
        return_value=None,
    )
    @patch("src.interfaces.mcp.tools.api.delete.transaction.atomic", return_value=nullcontext())
    def test_delete_api_case_revision_uses_version_service(
            self,
            _atomic,
            _validate,
            _impact,
            delete_revision,
    ):
        result = self.registry.tools["delete_api_case_revision"](8, 23)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"], {"case_id": 8, "revision_id": 23, "revision_no": 6})
        delete_revision.assert_called_once_with(8, 23)
