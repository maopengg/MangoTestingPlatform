from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService


class McpOwnedConfigurationTests(SimpleTestCase):

    @patch("src.apps.auto_api.services.api_info.runtime.ApiInfoMcpConfig.objects")
    @patch("src.apps.auto_api.services.api_info.runtime.ApiInfoGrpcConfig.objects")
    def test_saving_mcp_definition_persists_tool_snapshot_without_registry(self, grpc, configs):
        info = SimpleNamespace(protocol_type="mcp", _mcp_binding_snapshot={"tool_name": "search",
            "transport_type": 0, "input_schema": {"type": "object"}})
        ApiInfoRuntimeService.sync_protocol_config(info)
        saved = configs.update_or_create.call_args.kwargs["defaults"]
        self.assertEqual(saved["binding_snapshot"]["tool_name"], "search")
        self.assertEqual(saved["input_schema"], {"type": "object"})
        self.assertNotIn("mcp_tool", saved)

    @patch("src.apps.auto_api.services.api_info.runtime.ApiInfoMcpConfig.objects")
    def test_invalid_mcp_snapshot_cannot_silently_delete_valid_configuration(self, configs):
        with self.assertRaises(AutoApiError):
            ApiInfoRuntimeService.restore_mcp_binding(SimpleNamespace(protocol_type="mcp", _mcp_binding_snapshot={}))
        configs.filter.assert_not_called()
        configs.update_or_create.assert_not_called()

    @patch("src.apps.auto_api.services.api_info.runtime.ApiInfoMcpConfig.objects")
    def test_reading_tool_definition_does_not_require_old_tool_records(self, configs):
        configs.filter.return_value.first.return_value = SimpleNamespace(
            binding_snapshot={"tool_name": "search", "transport_type": 0}, mcp_config=None,
            input_schema={"type": "object"}, output_schema=None, schema_hash="schema")
        value = ApiInfoRuntimeService.capture_mcp_binding(SimpleNamespace(protocol_type="mcp", id=1))
        self.assertEqual(value["tool_name"], "search")
        self.assertEqual(value["schema_hash"], "schema")
