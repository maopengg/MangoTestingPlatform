from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.ai.api.serializers.mcp_server_mutation import AiMcpServerSerializer
from src.apps.ai.enums import AiMcpStatusEnum
from src.apps.ai.models import AiMcpServer
from src.apps.ai.services.core import McpService


class McpServerStatusTests(SimpleTestCase):
    @staticmethod
    def disabled_server() -> AiMcpServer:
        return AiMcpServer(
            id=2,
            name="已停用 MCP",
            server_url="https://example.com/mcp",
            status=AiMcpStatusEnum.DISABLED.value,
            last_test_time=timezone.now(),
            last_error=None,
        )

    @patch("src.apps.ai.services.core.ExternalMcpClient.list_capabilities")
    def test_disabled_server_skips_connection_test(self, list_capabilities):
        server = self.disabled_server()
        last_test_time = server.last_test_time

        result = McpService.test_server(server, user_id=1)

        list_capabilities.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertEqual(server.last_test_time, last_test_time)

    @patch.object(McpService, "list_capabilities_for_sync")
    def test_disabled_server_skips_tool_sync(self, list_capabilities_for_sync):
        result = McpService.sync_tools(self.disabled_server(), user_id=1)

        list_capabilities_for_sync.assert_not_called()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["count"], 0)

    def test_disabled_server_is_never_serialized_as_connected(self):
        self.assertFalse(AiMcpServerSerializer.get_is_connected(self.disabled_server()))
