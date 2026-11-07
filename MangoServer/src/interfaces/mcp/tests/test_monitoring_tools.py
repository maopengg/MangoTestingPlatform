import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase
from fastmcp import Client, FastMCP
from fastmcp.server.auth import AccessToken

from src.apps.monitoring.models import MonitoringTask
from src.apps.monitoring.presenters import task_data
from src.apps.monitoring.services.task_mutation import MonitoringTaskMutationService
from src.apps.user.selectors.authorization import AuthorizationScopeSelector
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, permission_error, resolve_project_product_ids
from src.interfaces.mcp.server import mcp_asgi_app, _tool_operation
from src.interfaces.mcp.tools.monitoring import register_monitoring_tools


class MonitoringToolsTests(SimpleTestCase):
    async def test_context_is_readonly_and_discoverable_for_authenticated_business_users(self):
        from src.apps.monitoring.selectors.script_context import MonitoringScriptContextSelector

        server = FastMCP('example-monitoring-context')
        register_monitoring_tools(server)
        with patch.object(MonitoringScriptContextSelector, 'get', return_value={'runtime': {'online_nodes': 0}}) as query:
            async with Client(server) as client:
                response = await client.call_tool('get_monitoring_script_context', {})
            query.assert_called_once_with()
            self.assertFalse(response.is_error)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'index.home:read'}):
            self.assertIsNone(permission_error(SimpleNamespace(id=7), 'get_monitoring_script_context', {}))
            self.assertIsNotNone(permission_error(SimpleNamespace(id=7), 'create_monitoring_task', {}))
        self.assertEqual(_tool_operation('get_monitoring_script_context'), 'read')

    async def test_root_and_monitoring_endpoints_list_tools_by_role(self):
        for grants, expected in ((['monitoring.task:read'], {'list_monitoring_tasks', 'get_monitoring_task', 'get_monitoring_task_logs'}),
                                 (['monitoring.task:change'], {'update_monitoring_task', 'control_monitoring_task'}),
                                 (['monitoring.task:add'], {'create_monitoring_task'})):
            access = AccessToken(token='example-key', client_id='example-client', subject='7', scopes=grants,
                                 claims={'user_id': 7, 'is_super_admin': False})
            with patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)):
                for domain in (None, 'monitoring'):
                    async with Client(mcp_asgi_app(domain).fastmcp_server) as client:
                        names = {tool.name for tool in await client.list_tools() if 'monitoring_task' in tool.name}
                    self.assertEqual(names, expected)

    def test_role_scope_and_mutation_classification(self):
        user = SimpleNamespace(id=7)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'monitoring.task:read'}):
            self.assertEqual(permission_error(user, 'control_monitoring_task', {'monitoring_task_id': 1, 'action': 'start'})['error_code'], 'MCP_PERMISSION_DENIED')
            with patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={2}), \
                    patch.object(ProjectProductScopeService, 'has_project_product', return_value=False):
                self.assertEqual(permission_error(user, 'get_monitoring_task', {'monitoring_task_id': 1})['error_code'], 'MCP_PROJECT_SCOPE_DENIED')
            with patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value=set()):
                self.assertEqual(permission_error(user, 'get_monitoring_task_logs', {'monitoring_task_id': 999})['error_code'], 'MCP_PROJECT_SCOPE_UNRESOLVED')
        with patch.object(AuthorizationScopeSelector, 'queryset') as query:
            query.return_value.filter.return_value.values_list.return_value.first.return_value = 2
            self.assertEqual(resolve_project_product_ids('control_monitoring_task', {'monitoring_task_id': 1}), {2})
            self.assertTrue(any(call.args == (MonitoringTask,) for call in query.call_args_list))
        for name, operation in (('create_monitoring_task', 'create'), ('update_monitoring_task', 'update'),
                                ('control_monitoring_task', 'execute'),
                                ('get_monitoring_task_logs', 'read')):
            self.assertEqual(_tool_operation(name), operation)

    async def test_create_calls_domain_service_with_typed_fields(self):
        server = FastMCP('example-monitoring')
        register_monitoring_tools(server)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.monitoring.current_user', return_value=user), \
                patch.object(MonitoringTaskMutationService, 'create', return_value=object()) as create, \
                patch('src.interfaces.mcp.tools.monitoring.task_data', return_value={'id': 9, 'status': 0}):
            async with Client(server) as client:
                response = await client.call_tool('create_monitoring_task', {
                    'project_product_id': 2, 'fields': {'name': '示例脚本', 'script_content': 'pass'}})
            self.assertFalse(response.is_error)
            self.assertEqual(json.loads(response.content[0].text)['data']['id'], 9)
            self.assertIs(create.call_args.args[0], user)
            self.assertEqual(create.call_args.args[2].script_content, 'pass')

    async def test_one_control_tool_dispatches_start_and_stop(self):
        from fastmcp.exceptions import ToolError

        server = FastMCP('example-monitoring')
        register_monitoring_tools(server)
        user = SimpleNamespace(id=7)
        with patch('src.interfaces.mcp.tools.monitoring.current_user', return_value=user), \
                patch.object(MonitoringTaskMutationService, 'start', return_value=object()) as start, \
                patch.object(MonitoringTaskMutationService, 'stop', return_value=object()) as stop, \
                patch('src.interfaces.mcp.tools.monitoring.task_data', return_value={'id': 9}):
            async with Client(server) as client:
                for action in ('start', 'stop'):
                    await client.call_tool('control_monitoring_task', {'monitoring_task_id': 9, 'action': action})
                with self.assertRaises(ToolError):
                    await client.call_tool('control_monitoring_task', {'monitoring_task_id': 9, 'action': 'restart'})
            start.assert_called_once_with(user, 9)
            stop.assert_called_once_with(user, 9)

    def test_presenter_does_not_expose_paths_or_pid_and_script_is_opt_in(self):
        task = MonitoringTask(id=1, name='示例', project_product_id=2, script_content='pass')
        data = task_data(task)
        self.assertNotIn('script_content', data)
        self.assertNotIn('log_path', data)
        self.assertNotIn('pid', data)
        self.assertEqual(task_data(task, include_script=True)['script_content'], 'pass')

    def test_typed_script_fields_are_not_written_to_operation_logs(self):
        from src.apps.monitoring.schemas.task import MonitoringTaskCreate
        from src.interfaces.mcp.common import _json_dumps_limited

        payload = {'fields': MonitoringTaskCreate(name='示例', script_content='private-script-example')}
        text = _json_dumps_limited(payload)
        self.assertNotIn('private-script-example', text)
        self.assertEqual(json.loads(text)['fields']['script_content'], '***')
