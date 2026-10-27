import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from fastmcp import Client, FastMCP
from fastmcp.server.auth import AccessToken

from src.apps.test_center.enums import ReportFailureReasonEnum
from src.apps.test_center.services.test_suite.disposition import TestSuiteDispositionService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, component_policy, permission_error
from src.interfaces.mcp.server import mcp_asgi_app, _tool_operation
from src.interfaces.mcp.tools.report.test_report import register_test_report_tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func
        return register


class ReportCaseDiagnosisMcpTests(SimpleTestCase):
    name = 'update_test_report_case_diagnosis'

    def test_tool_forwards_only_diagnosis_fields_to_shared_service(self):
        registry = ToolRegistry()
        register_test_report_tools(registry)
        tool = registry.tools[self.name]
        self.assertIsNone(inspect.signature(tool).parameters['is_excluded'].default)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.report.test_report.current_user', return_value=user), \
                patch.object(TestSuiteDispositionService, 'update_diagnosis', return_value={
                    'failure_reason': 'product_pending', 'failure_description': '代码违反已确认契约',
                    'is_excluded': False,
                }) as update:
            result = tool(123, ReportFailureReasonEnum.PRODUCT_PENDING, '代码违反已确认契约')
        update.assert_called_once_with(123, 'product_pending', '代码违反已确认契约', user=user, is_excluded=None)
        self.assertEqual(result['data']['test_suite_detail_id'], 123)
        self.assertFalse(result['data']['is_excluded'])

    def test_reason_schema_and_permission_use_shared_definitions(self):
        server = FastMCP('diagnosis-schema')
        register_test_report_tools(server)
        tools = {tool.name: tool for tool in async_to_sync(server.list_tools)(run_middleware=False)}
        schema = tools[self.name].parameters
        reason = schema['properties']['failure_reason']
        if '$ref' in reason:
            reason = schema['$defs'][reason['$ref'].split('/')[-1]]
        self.assertEqual(set(reason['enum']), set(ReportFailureReasonEnum.obj()))
        self.assertNotIn('is_excluded', schema.get('required', []))
        self.assertIn('true=排除', json.dumps(schema['properties']['is_excluded'], ensure_ascii=False))
        self.assertEqual(_tool_operation(self.name), 'update')
        self.assertEqual(component_policy(self.name).permission_key, 'report:exclude')
        with patch('src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch('src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user', return_value={'report:detail'}):
            result = permission_error(SimpleNamespace(id=7), self.name, {'test_suite_detail_id': 123})
        self.assertEqual(result['error_code'], 'MCP_PERMISSION_DENIED')

    async def test_authorized_tools_list_discovers_tool_in_root_and_report_servers(self):
        for scopes, expected in [(['report:exclude'], True), (['report:detail'], False)]:
            access = AccessToken(token='test-diagnosis-key', client_id='diagnosis-test', subject='7',
                                 scopes=scopes, claims={'user_id': 7, 'is_super_admin': False})
            with patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)):
                for domain in (None, 'report'):
                    server = mcp_asgi_app(domain).fastmcp_server
                    async with Client(server) as client:
                        tools = {tool.name: tool for tool in await client.list_tools()}
                    self.assertEqual(self.name in tools, expected)
                    if expected:
                        self.assertIn('is_excluded', tools[self.name].inputSchema['properties'])

    async def test_mcp_call_accepts_canonical_string_value(self):
        server = FastMCP('diagnosis-call')
        register_test_report_tools(server)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.report.test_report.current_user', return_value=user), \
                patch.object(TestSuiteDispositionService, 'update_diagnosis', return_value={
                    'failure_reason': 'test_case', 'failure_description': '断言与已确认契约不一致',
                    'is_excluded': True,
                }) as update:
            async with Client(server) as client:
                response = await client.call_tool(self.name, {
                    'test_suite_detail_id': 123, 'failure_reason': 'test_case',
                    'failure_description': '断言与已确认契约不一致',
                })
        self.assertFalse(response.is_error)
        update.assert_called_once_with(123, 'test_case', '断言与已确认契约不一致', user=user, is_excluded=None)

    async def test_mcp_exclusion_switch_values_and_invalid_string(self):
        server = FastMCP('exclusion-call')
        register_test_report_tools(server)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.report.test_report.current_user', return_value=user), \
                patch.object(TestSuiteDispositionService, 'update_diagnosis', return_value={'is_excluded': True}) as update:
            async with Client(server) as client:
                for value in (True, False, None):
                    response = await client.call_tool(self.name, {
                        'test_suite_detail_id': 123, 'failure_reason': 'test_case',
                        'failure_description': '断言与已确认契约不一致', 'is_excluded': value,
                    })
                    self.assertFalse(response.is_error)
                    self.assertIs(update.call_args.kwargs['is_excluded'], value)
                update.reset_mock()
                response = await client.call_tool(self.name, {
                    'test_suite_detail_id': 123, 'failure_reason': 'test_case',
                    'failure_description': '说明', 'is_excluded': 'false',
                }, raise_on_error=False)
                self.assertTrue(response.is_error)
                update.assert_not_called()
