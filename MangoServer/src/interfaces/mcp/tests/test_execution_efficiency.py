from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import json

from django.test import SimpleTestCase
from fastmcp import Client, FastMCP
from fastmcp.server.auth import AccessToken

from src.apps.test_center.services.reporting.execution_efficiency import ExecutionEfficiencyService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware
from src.interfaces.mcp.server import mcp_asgi_app, _tool_operation
from src.interfaces.mcp.tools.report.execution_efficiency import register_execution_efficiency_tools


class ExecutionEfficiencyMcpTests(SimpleTestCase):
    async def test_authorized_tools_list_in_root_and_report_endpoints(self):
        for scopes, expected in ((['report.execution_efficiency:read'], True), (['report:read'], False)):
            access = AccessToken(token='test-efficiency-key', client_id='efficiency-test', subject='7',
                                 scopes=scopes, claims={'user_id': 7, 'is_super_admin': False})
            with patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)):
                for domain in (None, 'report'):
                    async with Client(mcp_asgi_app(domain).fastmcp_server) as client:
                        names = {tool.name for tool in await client.list_tools()}
                    self.assertEqual('list_execution_efficiency' in names, expected)

    async def test_shared_query_and_default_pagination(self):
        server = FastMCP('efficiency-test')
        register_execution_efficiency_tools(server)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.report.execution_efficiency.current_user', return_value=user), \
                patch.object(ExecutionEfficiencyService, 'query', return_value={
                    'summary': {}, 'phases': [], 'basic': [], 'trend': [], 'slow_reports': [],
                    'slow_cases': [{'id': index} for index in range(25)],
                }) as query:
            async with Client(server) as client:
                response = await client.call_tool('list_execution_efficiency', {'section': 'timing'})
            self.assertFalse(response.is_error)
            result = json.loads(response.content[0].text)['data']
            self.assertEqual(len(result['items']), 10)
            self.assertEqual(result['count'], 25)
            values = query.call_args.args[1]
            self.assertEqual(values.page_size, 10)
            self.assertEqual(values.section, 'timing')
            self.assertEqual(_tool_operation('list_execution_efficiency'), 'read')
