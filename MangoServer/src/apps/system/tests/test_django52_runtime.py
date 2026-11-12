import asyncio
import os
from unittest import TestCase
from unittest.mock import Mock, patch

import django
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import AsyncClient, SimpleTestCase
from django.urls import resolve, Resolver404
from rest_framework.exceptions import ValidationError

from src.apps.data_factory.enums import DataFactoryErrorCodeEnum
from src.apps.data_factory.exceptions import DATA_FACTORY_DELETE_NOT_FOUND, DataFactoryError
from src.interfaces.mcp.server import _authenticated_tool_method, _logged_public_tool
from src.processes.server_logging import access_log_enabled


class ManagementHealthTests(SimpleTestCase):
    def test_runtime_uses_django_52_lts(self):
        self.assertEqual(django.VERSION[:2], (5, 2))

    def test_django_52_storage_configuration_is_enabled(self):
        self.assertIn('daphne', settings.INSTALLED_APPS)
        self.assertIn('django.contrib.staticfiles', settings.INSTALLED_APPS)
        self.assertEqual(
            settings.STORAGES['staticfiles']['BACKEND'],
            'django.contrib.staticfiles.storage.StaticFilesStorage',
        )

    def test_success_access_logs_only_use_info_level_in_dev(self):
        expected_level = 'INFO' if settings.DJANGO_ENV == 'dev' else 'WARNING'

        self.assertEqual(settings.LOGGING['loggers']['django.server']['level'], expected_level)
        self.assertEqual(settings.LOGGING['loggers']['uvicorn.access']['level'], expected_level)

    async def test_management_health_returns_ok(self):
        with patch('src.urls._check_database_connection') as check_database_connection:
            response = await AsyncClient().get('/management/health')

        check_database_connection.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    async def test_management_health_returns_503_when_database_unavailable(self):
        with patch('src.urls._check_database_connection', side_effect=ConnectionError):
            response = await AsyncClient().get('/management/health')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'error', 'database': 'unavailable'})

    async def test_legacy_anonymous_runtime_endpoints_are_removed(self):
        for action in ('overview', 'services', 'queues', 'diagnostics', 'recent-errors'):
            path = f'/management/runtime/{action}'
            with self.subTest(path=path):
                with self.assertRaises(Resolver404):
                    resolve(path)
                response = await AsyncClient().get(path)
                self.assertEqual(response.status_code, 404)

    def test_runtime_endpoints_keep_role_permissions_and_reject_anonymous_requests(self):
        from types import SimpleNamespace
        from django.http import QueryDict
        from rest_framework.test import APIRequestFactory
        from src.apps.user.middleware.permission import MenuActionPermission
        from src.apps.user.services.authorization.permission import PermissionMenuService
        from src.apps.user.services.authorization.http_permission_registry import permission_for_view

        guest_keys = PermissionMenuService.guest_permission_keys()
        for action in ('overview', 'services', 'queues', 'diagnostics', 'recent-errors'):
            path = f'/api/system/runtime/{action}'
            match = resolve(path)
            view = match.func.cls()
            view.action = match.func.actions['get']
            required = 'system.error_record:read' if action == 'recent-errors' else 'system.runtime_center:read'
            self.assertEqual(permission_for_view(view, view.action, 'get'), required)
            response = match.func(APIRequestFactory().get(path))
            self.assertNotEqual(response.data['code'], 200)
            for keys, allowed in (({required}, True), (guest_keys, False), ({'index.home:read'}, False)):
                with self.subTest(path=path, allowed=allowed), \
                        patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                        patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=keys):
                    request = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(),
                                              user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
                    self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)


class McpRuntimeTests(TestCase):
    def test_uvicorn_access_log_is_only_enabled_in_dev(self):
        with patch.dict(os.environ, {'DJANGO_ENV': 'dev'}):
            self.assertTrue(access_log_enabled())
        with patch.dict(os.environ, {'DJANGO_ENV': 'test'}):
            self.assertFalse(access_log_enabled())
        with patch.dict(os.environ, {'DJANGO_ENV': 'master'}):
            self.assertFalse(access_log_enabled())

    def test_mcp_asgi_application_is_importable(self):
        from src.processes.mcp.asgi import application

        self.assertTrue(callable(application))

    def test_mcp_asgi_lifespan_starts_and_stops(self):
        from src.asgi import application

        messages = iter([
            {'type': 'lifespan.startup'},
            {'type': 'lifespan.shutdown'},
        ])
        sent = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        asyncio.run(application(
            {'type': 'lifespan', 'asgi': {'version': '3.0', 'spec_version': '2.0'}},
            receive,
            send,
        ))

        self.assertEqual(sent, [
            {'type': 'lifespan.startup.complete'},
            {'type': 'lifespan.shutdown.complete'},
        ])

    def test_run_mcp_service_uses_import_string_for_multi_worker(self):
        from src.processes.mcp import runner

        with patch.object(runner, 'DrainingMcpServer') as server, \
                patch.object(runner.uvicorn.Config, 'bind_socket') as bind, \
                patch('uvicorn.supervisors.Multiprocess') as supervisor:
            runner.run_mcp_service('127.0.0.1', 8010, workers=3)
        config = server.call_args.args[0]
        self.assertEqual(config.app, runner.MCP_ASGI_APPLICATION)
        self.assertEqual(config.workers, 3)
        self.assertEqual(config.access_log, access_log_enabled())
        self.assertEqual(supervisor.call_args.kwargs['target'], server.return_value.run)
        supervisor.return_value.run.assert_called_once()
        bind.return_value.close.assert_called_once()

    def test_run_realtime_service_uses_environment_access_log_setting(self):
        from src.processes.realtime import runner

        with patch.object(runner.uvicorn, 'run') as uvicorn_run:
            runner.run_realtime_service('127.0.0.1', 8011)

        uvicorn_run.assert_called_once_with(
            runner.REALTIME_ASGI_APPLICATION,
            host='127.0.0.1',
            port=8011,
            workers=1,
            lifespan='on',
            access_log=access_log_enabled(),
        )

    def test_authenticated_tool_method_supports_async_tool(self):
        fake_mcp = Mock()
        fake_mcp.tool.return_value = lambda func: func

        async def sample_tool(value):
            return {'success': True, 'data': value}

        with patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async'), \
                patch('src.interfaces.mcp.authentication.permission_error', return_value=None), \
                patch('src.interfaces.mcp.authentication.filter_scoped_result', side_effect=lambda _user, value: value):
            decorated = _authenticated_tool_method(fake_mcp, 'system')()(sample_tool)
            result = asyncio.run(decorated('ok'))

        self.assertEqual(result, {'success': True, 'data': 'ok'})

    def test_authenticated_sync_tool_converts_missing_object_without_system_record(self):
        fake_mcp = Mock()
        fake_mcp.tool.return_value = lambda func: func

        def sample_tool():
            raise ObjectDoesNotExist('internal model name')

        with patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async') as log_call, \
                patch('src.interfaces.mcp.authentication.filter_scoped_result', side_effect=lambda _user, value: value), \
                patch('src.interfaces.mcp.server._report_mcp_system_error') as report_system_error:
            decorated = _authenticated_tool_method(fake_mcp, 'system')()(sample_tool)
            result = decorated()

        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], '300')
        self.assertEqual(result['message'], '指定的数据不存在或已删除，请重新查询后使用有效ID')
        report_system_error.assert_not_called()
        self.assertEqual(log_call.call_args.kwargs['status_code'], 404)

    def test_authenticated_async_tool_converts_domain_error_without_system_record(self):
        fake_mcp = Mock()
        fake_mcp.tool.return_value = lambda func: func

        async def sample_tool():
            raise DataFactoryError(
                DATA_FACTORY_DELETE_NOT_FOUND,
                error_code=DataFactoryErrorCodeEnum.TEST_OBJECT_NOT_FOUND.value,
                details={'test_object_id': 6104},
            )

        with patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async') as log_call, \
                patch('src.interfaces.mcp.authentication.filter_scoped_result', side_effect=lambda _user, value: value), \
                patch('src.interfaces.mcp.server._report_mcp_system_error') as report_system_error:
            decorated = _authenticated_tool_method(fake_mcp, 'system')()(sample_tool)
            result = asyncio.run(decorated())

        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'TEST_OBJECT_NOT_FOUND')
        self.assertEqual(result['details'], {'test_object_id': 6104})
        report_system_error.assert_not_called()
        self.assertEqual(log_call.call_args.kwargs['status_code'], 400)

    def test_authenticated_tool_still_records_unknown_error(self):
        fake_mcp = Mock()
        fake_mcp.tool.return_value = lambda func: func

        def sample_tool():
            raise RuntimeError('boom')

        with patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async') as log_call, \
                patch('src.interfaces.mcp.authentication.filter_scoped_result', side_effect=lambda _user, value: value), \
                patch('src.interfaces.mcp.server._report_mcp_system_error') as report_system_error:
            decorated = _authenticated_tool_method(fake_mcp, 'system')()(sample_tool)
            result = decorated()

        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'MCP_TOOL_EXCEPTION')
        report_system_error.assert_called_once()
        self.assertEqual(log_call.call_args.kwargs['status_code'], 500)

    def test_authenticated_tool_does_not_record_validation_error_as_system_error(self):
        fake_mcp = Mock()
        fake_mcp.tool.return_value = lambda func: func

        def sample_tool():
            raise ValidationError({'json_path': ['Extra inputs are not permitted']})

        with patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async') as log_call, \
                patch('src.interfaces.mcp.authentication.filter_scoped_result', side_effect=lambda _user, value: value), \
                patch('src.interfaces.mcp.server._report_mcp_system_error') as report_system_error:
            decorated = _authenticated_tool_method(fake_mcp, 'system')()(sample_tool)
            result = decorated()

        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'VALIDATION_ERROR')
        report_system_error.assert_not_called()
        self.assertEqual(log_call.call_args.kwargs['status_code'], 400)

    def test_logged_public_tool_supports_async_tool(self):
        async def sample_tool(value):
            return {'success': True, 'data': value}

        with patch('src.interfaces.mcp.common.user_from_auth_token', return_value=Mock(role=None)), \
                patch('src.interfaces.mcp.common.log_mcp_tool_call_async'):
            result = asyncio.run(_logged_public_tool(sample_tool)('ok'))

        self.assertEqual(result, {'success': True, 'data': 'ok'})

    def test_project_context_read_tools_run_in_worker_threads(self):
        from src.interfaces.mcp.server import mcp_asgi_app

        server = mcp_asgi_app().fastmcp_server

        for tool_name in [
            'list_test_environments',
            'list_project_test_objects',
            'list_project_products',
            'list_product_modules',
        ]:
            tool = async_to_sync(server.get_tool)(tool_name)
            self.assertTrue(tool.run_in_thread, tool_name)

    def test_simple_mcp_resources_are_registered(self):
        from src.interfaces.mcp.server import mcp_asgi_app

        server = mcp_asgi_app().fastmcp_server
        resource_names = {item.name for item in async_to_sync(server._list_resource_templates)()}

        for resource_name in [
            'get_project_product_resource',
            'get_api_info_resource',
            'get_data_factory_entity_resource',
            'get_data_factory_template_resource',
            'get_data_factory_case_config_resource',
            'get_ui_page_resource',
            'get_ui_page_step_resource',
        ]:
            self.assertIn(resource_name, resource_names)
