import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
from asgiref.sync import async_to_sync
from django.test import SimpleTestCase, override_settings
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import AuthorizationError, ToolError
from fastmcp.server.auth import AccessToken
from mcp.server.fastmcp import FastMCP as OldFastMCP

from src.apps.user.models import User
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService
from src.interfaces.mcp.authentication import (
    TOKEN_VERIFIER,
    MangoAuthorizationMiddleware,
    MangoTokenVerifier,
    component_policy,
    permission_error,
)
from src.interfaces.mcp.server import MCP_DOMAIN_PATHS, mcp_asgi_app, mcp_router_asgi_app
from src.interfaces.mcp.tools.evaluation import register_evaluation_tools
from src.interfaces.mcp.tools.api import register_api_tools
from src.interfaces.mcp.tools.data_factory import register_data_factory_tools
from src.interfaces.mcp.tools.functional_test import register_functional_test_tools
from src.interfaces.mcp.tools.project import register_project_tools
from src.interfaces.mcp.tools.project.context import register_project_context_tools
from src.interfaces.mcp.tools.pytest import register_pytest_tools
from src.interfaces.mcp.tools.report import register_report_tools
from src.interfaces.mcp.tools.scheduled_task import register_scheduled_task_tools
from src.interfaces.mcp.tools.system import register_system_tools
from src.interfaces.mcp.tools.ui import register_ui_tools

TOOL_REGISTRARS = [
    register_evaluation_tools,
    register_project_tools,
    register_api_tools,
    register_ui_tools,
    register_pytest_tools,
    register_scheduled_task_tools,
    register_data_factory_tools,
    register_system_tools,
    register_report_tools,
    register_functional_test_tools,
]


@override_settings(
    MCP_ALLOWED_HOSTS=["mango-platform.example.com"],
    MCP_ALLOWED_ORIGINS=["https://mango-platform.example.com"],
)
class FastMcpMigrationTests(SimpleTestCase):
    def setUp(self):
        from src.apps.user.tests.permission_fixtures import install_legacy_endpoint_snapshot
        install_legacy_endpoint_snapshot(self)

    def test_list_product_modules_applies_pagination(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_project_context_tools(capture)
        project_product = SimpleNamespace(name="测试产品")
        module = SimpleNamespace(
            id=2,
            name="第二个模块",
            project_product_id=1,
            project_product=project_product,
            parent_id=None,
            parent=None,
            level=1,
        )
        queryset = MagicMock()
        queryset.count.return_value = 3
        queryset.__getitem__.return_value = [module]

        with patch(
                "src.interfaces.mcp.tools.project.context.TestCenterQuerySelector.product_module"
        ) as module_selector:
            module_selector.return_value.filter.return_value.select_related.return_value.order_by.return_value = queryset
            result = capture.tools["list_product_modules"](
                project_product_id=1,
                page=2,
                page_size=1,
            )

        queryset.__getitem__.assert_called_once_with(slice(1, 2, None))
        self.assertEqual(result["data"]["count"], 3)
        self.assertEqual(result["data"]["page"], 2)
        self.assertEqual(result["data"]["page_size"], 1)
        self.assertEqual(result["data"]["items"][0]["id"], 2)

    def test_update_product_module_supports_changing_parent(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_project_context_tools(capture)

        module = SimpleNamespace(
            id=3,
            name="订单查询",
            project_product_id=1,
            project_product=SimpleNamespace(name="测试产品"),
            parent_id=2,
            parent=SimpleNamespace(id=2, name="订单管理", parent=None),
            level=3,
        )
        with (
            patch(
                "src.interfaces.mcp.tools.project.context.ProductModuleService.update",
                return_value=module,
            ) as update_module,
            patch(
                "src.interfaces.mcp.tools.project.context.current_user",
                return_value=SimpleNamespace(id=7),
            ),
        ):
            result = capture.tools["update_product_module"](
                module_id=3,
                name="订单查询",
                parent_id=2,
            )

        update_module.assert_called_once_with(
            3,
            {"id": 3, "name": "订单查询", "parent": 2, "update_user": 7},
        )
        self.assertEqual(result["data"]["module"]["parent_id"], 2)

    def test_registered_component_counts_are_preserved(self):
        server = mcp_asgi_app().fastmcp_server
        old_server = OldFastMCP("old")
        for registrar in TOOL_REGISTRARS:
            registrar(old_server)

        tools = async_to_sync(server.list_tools)(run_middleware=False)
        old_tools = async_to_sync(old_server.list_tools)()
        resource_templates = async_to_sync(server._list_resource_templates)()
        prompts = async_to_sync(server._list_prompts)()

        added_tools = {
            "get_monitoring_script_context",
            "list_monitoring_tasks", "get_monitoring_task", "get_monitoring_task_logs",
            "create_monitoring_task", "update_monitoring_task", "control_monitoring_task",
            "get_mcp_server_info",
            "list_mcp_skills",
            "get_mcp_skill",
            "list_workbench_todos",
            "get_workbench_todo_detail",
            "refresh_workbench_todos",
            "update_workbench_todo_handled",
        }
        self.assertEqual(
            {tool.name for tool in tools},
            {tool.name for tool in old_tools} | added_tools,
        )
        self.assertEqual(len(resource_templates), 16)
        self.assertEqual(len(prompts), 5)

    def test_copy_operations_are_not_exposed_as_mcp_tools(self):
        tools = async_to_sync(
            mcp_asgi_app().fastmcp_server.list_tools
        )(run_middleware=False)
        tool_names = {tool.name for tool in tools}
        self.assertTrue(
            {
                "copy_api_case_scenario",
                "copy_ui_case",
                "copy_ui_page_step",
            }.isdisjoint(tool_names)
        )

    def test_scheduled_task_mcp_does_not_expose_create(self):
        class ToolCapture:
            def __init__(self):
                self.tools = set()

            def tool(self):
                def register(func):
                    self.tools.add(func.__name__)
                    return func

                return register

        capture = ToolCapture()
        register_scheduled_task_tools(capture)

        self.assertEqual(
            capture.tools,
            {
                "upload_scheduled_task_diagnostic_markdown",
                "list_scheduled_task_strategies",
                "list_scheduled_tasks",
                "get_scheduled_task_detail",
                "list_scheduled_task_cases",
                "preview_trigger_scheduled_task_impact",
                "trigger_scheduled_task",
                "preview_bind_cases_to_scheduled_task_impact",
                "bind_cases_to_scheduled_task",
                "preview_unbind_cases_from_scheduled_task_impact",
                "unbind_cases_from_scheduled_task",
            },
        )

    def test_report_mcp_removes_separate_trend_and_retry_preview_tools(self):
        class ToolCapture:
            def __init__(self):
                self.tools = set()

            def tool(self):
                def register(func):
                    self.tools.add(func.__name__)
                    return func

                return register

        capture = ToolCapture()
        register_report_tools(capture)

        self.assertTrue(
            {
                "get_test_report_trend",
                "preview_retry_test_report_case_impact",
                "preview_retry_test_report_impact",
            }.isdisjoint(capture.tools)
        )
        self.assertIn("retry_test_report_case", capture.tools)
        self.assertIn("retry_test_report", capture.tools)


    def test_native_fastmcp_schemas_replace_legacy_schema_adapter(self):
        old_server = OldFastMCP("old")
        migrated_server = mcp_asgi_app().fastmcp_server
        for registrar in TOOL_REGISTRARS:
            registrar(old_server)

        old_tools = async_to_sync(old_server.list_tools)()
        new_tools = async_to_sync(migrated_server.list_tools)(run_middleware=False)
        old_by_name = {tool.name: tool for tool in old_tools}
        new_by_name = {tool.name: tool for tool in new_tools}

        additional_names = {
            "get_monitoring_script_context",
            "list_monitoring_tasks", "get_monitoring_task", "get_monitoring_task_logs",
            "create_monitoring_task", "update_monitoring_task", "control_monitoring_task",
            "get_mcp_server_info",
            "list_mcp_skills",
            "get_mcp_skill",
            "list_workbench_todos",
            "get_workbench_todo_detail",
            "refresh_workbench_todos",
            "update_workbench_todo_handled",
        }
        self.assertEqual(old_by_name.keys(), new_by_name.keys() - additional_names)
        for name in old_by_name:
            self.assertTrue(new_by_name[name].description, name)
            self.assertEqual(new_by_name[name].parameters["type"], "object", name)
            self.assertIn("additionalProperties", new_by_name[name].parameters, name)
            self.assertIsNotNone(new_by_name[name].output_schema, name)

    def test_tools_expose_standard_annotations_and_domain_metadata(self):
        tools = {
            tool.name: tool
            for tool in async_to_sync(mcp_asgi_app().fastmcp_server.list_tools)(run_middleware=False)
        }

        self.assertTrue(tools["list_api_headers"].annotations.readOnlyHint)
        self.assertFalse(tools["create_api_header"].annotations.readOnlyHint)
        self.assertTrue(tools["delete_api_case"].annotations.destructiveHint)
        self.assertEqual(tools["list_api_headers"].meta["mango"]["domain"], "api")
        self.assertEqual(tools["list_system_files"].meta["mango"]["domain"], "file")

    def test_every_component_has_an_authorization_policy(self):
        root = Path(__file__).resolve().parents[1] / "src/interfaces/mcp"
        missing = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    target = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "mcp"
                            and target.attr in {"tool", "resource", "prompt"}
                            and component_policy(node.name) is None
                    ):
                        missing.append(node.name)

        self.assertEqual(missing, [])

    def test_every_policy_uses_an_existing_role_permission_key(self):
        server = mcp_asgi_app().fastmcp_server
        components = [
            *async_to_sync(server.list_tools)(run_middleware=False),
            *async_to_sync(server._list_resource_templates)(),
            *async_to_sync(server._list_prompts)(),
        ]
        valid_keys = PermissionMenuService.all_permission_keys()
        invalid = {
            component.name: component_policy(component.name).permission_key
            for component in components
            if component_policy(component.name).permission_key
               and component_policy(component.name).permission_key not in valid_keys
        }

        self.assertEqual(invalid, {})

    def test_anonymous_users_only_see_public_tools(self):
        middleware = MangoAuthorizationMiddleware()
        public = SimpleNamespace(name="get_mcp_server_info")
        protected = SimpleNamespace(name="list_api_headers")

        self.assertTrue(middleware._visible(None, public.name))
        self.assertFalse(middleware._visible(None, protected.name))

    def test_permissions_reuse_existing_role_keys(self):
        self.assertEqual(component_policy("list_api_headers").permission_key, "api.headers:read")
        self.assertEqual(component_policy("create_api_header").permission_key, "api.headers:add")
        self.assertEqual(component_policy("query_data_factory_datasource_redis").permission_key, "config.product:change")
        self.assertEqual(component_policy("delete_api_case").permission_key, "api.case:remove")
        self.assertEqual(component_policy("get_api_auth_config_cache").permission_key, "api.auth_config:read")
        self.assertEqual(component_policy("get_system_file_download_url").permission_key, "config.test_files:read")
        self.assertEqual(component_policy("create_ui_page_step_detail").permission_key, "ui.page_steps:add")
        self.assertEqual(component_policy("update_ui_page_step_detail").permission_key, "ui.page_steps:change")
        self.assertEqual(component_policy("delete_ui_page_step_detail").permission_key, "ui.page_steps:remove")
        self.assertTrue(component_policy("get_data_factory_table_schema").project_scoped)
        self.assertTrue(component_policy("auto_generate_api_case_scenario_schema").project_scoped)
        self.assertIsNone(component_policy("unknown_component"))

    async def test_anonymous_client_only_lists_public_tools(self):
        server = mcp_asgi_app().fastmcp_server

        async with Client(server) as client:
            tools = await client.list_tools()
            resources = await client.list_resource_templates()
            prompts = await client.list_prompts()

        self.assertEqual({tool.name for tool in tools}, {"get_mcp_server_info"})
        self.assertEqual(resources, [])
        self.assertEqual(prompts, [])

    async def test_direct_unauthenticated_tool_call_is_rejected_by_middleware(self):
        server = mcp_asgi_app().fastmcp_server

        async with Client(server) as client:
            with self.assertRaisesRegex(ToolError, "服务端未获取到 MCP Authorization 请求头"):
                await client.call_tool("get_api_case_schema", {})

    async def test_invalid_permanent_api_key_has_specific_error_message(self):
        middleware = MangoAuthorizationMiddleware()
        with (
            patch.object(middleware, "_access", new=AsyncMock(return_value=None)),
            patch("src.interfaces.mcp.authentication.bearer_token", return_value="mango_invalid_key"),
        ):
            with self.assertRaisesRegex(AuthorizationError, "APIKey 永久有效，不会自动过期"):
                await middleware._authorize("get_api_case_schema")

    async def test_invalid_login_jwt_has_specific_error_message(self):
        middleware = MangoAuthorizationMiddleware()
        with (
            patch.object(middleware, "_access", new=AsyncMock(return_value=None)),
            patch("src.interfaces.mcp.authentication.bearer_token", return_value="invalid.jwt.token"),
        ):
            with self.assertRaisesRegex(AuthorizationError, "登录 JWT，但 JWT 无效或已过期"):
                await middleware._authorize("get_api_case_schema")

    async def test_authenticated_tool_list_is_filtered_by_role_permissions(self):
        server = mcp_asgi_app().fastmcp_server
        access = AccessToken(
            token="mango_key",
            client_id="tester",
            subject="7",
            scopes=["api.headers:read"],
            claims={"user_id": 7, "is_super_admin": False, "endpoint_permissions":
                    EndpointPermissionService.from_legacy_keys({'api.headers:read'})},
        )
        with patch.object(MangoAuthorizationMiddleware, "_access", new=AsyncMock(return_value=access)):
            async with Client(server) as client:
                tools = await client.list_tools()

        names = {tool.name for tool in tools}
        self.assertIn("list_api_headers", names)
        self.assertNotIn("create_api_header", names)
        self.assertNotIn("list_data_factory_datasource_aliases", names)

    async def test_super_admin_sees_every_component(self):
        server = mcp_asgi_app().fastmcp_server
        all_tools = await server.list_tools(run_middleware=False)
        access = AccessToken(
            token="mango_admin_key",
            client_id="admin",
            subject="1",
            scopes=[],
            claims={"user_id": 1, "is_super_admin": True},
        )
        with patch.object(MangoAuthorizationMiddleware, "_access", new=AsyncMock(return_value=access)):
            async with Client(server) as client:
                tools = await client.list_tools()
                static_resources = await client.list_resources()
                resources = await client.list_resource_templates()
                prompts = await client.list_prompts()

        self.assertEqual(len(tools), len(all_tools))
        self.assertIn(
            "mango://skills/catalog",
            {str(resource.uri) for resource in static_resources},
        )
        self.assertEqual(len(resources), 16)
        self.assertIn("get_mcp_skill_resource", {resource.name for resource in resources})
        self.assertEqual(len(prompts), 5)
        self.assertIn("use_mcp_skill", {prompt.name for prompt in prompts})

    async def test_authorized_role_can_call_existing_tool_without_response_change(self):
        server = mcp_asgi_app().fastmcp_server
        user = SimpleNamespace(id=7, username="tester", role_id=3, is_super_admin=False)
        access = AccessToken(
            token="mango_key",
            client_id="tester",
            subject="7",
            scopes=["api.case:read"],
            claims={"user_id": 7, "is_super_admin": False},
        )
        with (
            patch("src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names", return_value={}),
            patch.object(MangoAuthorizationMiddleware, "_access", new=AsyncMock(return_value=access)),
            patch("src.interfaces.mcp.authentication.UserQuerySelector.user") as user_selector,
            patch("src.interfaces.mcp.common.require_mcp_user", return_value=None),
            patch("src.interfaces.mcp.common.user_from_auth_token", return_value=user),
            patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin",
                  return_value=False),
            patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
                  return_value={"api.case:read"}),
            patch("src.interfaces.mcp.authentication.ProjectProductScopeService.project_product_ids_for_user",
                  return_value=set()),
            patch("src.interfaces.mcp.authentication.ProjectProductScopeService.can_view_all_project_data",
                  return_value=True),
            patch("src.interfaces.mcp.common.log_mcp_tool_call_async"),
        ):
            user_selector.return_value.select_related.return_value.get.return_value = user
            async with Client(server) as client:
                result = await client.call_tool("get_api_case_schema", {})

        self.assertTrue(result.data["success"])
        self.assertEqual(result.data["message"], "操作成功")

    async def test_authenticated_client_can_discover_and_update_mcp_skills(self):
        server = mcp_asgi_app("data-factory").fastmcp_server
        access = AccessToken(
            token="mango_key",
            client_id="tester",
            subject="7",
            scopes=[],
            claims={"user_id": 7, "is_super_admin": False},
        )
        user = SimpleNamespace(id=7, username="tester", role_id=3, is_super_admin=False)
        with (
            patch.object(MangoAuthorizationMiddleware, "_access", new=AsyncMock(return_value=access)),
            patch("src.interfaces.mcp.authentication.UserQuerySelector.user") as user_selector,
            patch("src.interfaces.mcp.common.require_mcp_user", return_value=None),
            patch("src.interfaces.mcp.common.user_from_auth_token", return_value=user),
            patch("src.interfaces.mcp.common.log_mcp_tool_call_async"),
        ):
            user_selector.return_value.select_related.return_value.get.return_value = user
            async with Client(server) as client:
                catalog_resource = await client.read_resource("mango://skills/catalog")
                catalog_result = await client.call_tool("list_mcp_skills", {"page_size": 100})
                data_factory_skill = next(
                    item
                    for item in catalog_result.data["data"]["items"]
                    if item["name"] == "mango-data-factory-builder"
                )
                skill_result = await client.call_tool(
                    "get_mcp_skill",
                    {
                        "skill_name": "mango-data-factory-builder",
                        "known_version": data_factory_skill["version"],
                    },
                )

        self.assertIn("mango-data-factory-builder", catalog_resource[0].text)
        self.assertTrue(catalog_result.data["success"])
        self.assertTrue(skill_result.data["data"]["not_modified"])
        self.assertEqual(skill_result.data["data"]["files"], [])

    async def test_streamable_http_requires_bearer_authentication(self):
        app = mcp_asgi_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="https://mango-platform.example.com",
            ) as client:
                response = await client.post(
                    "/",
                    headers={"accept": "application/json, text/event-stream"},
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "1.0"},
                        },
                    },
                )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    async def test_streamable_http_authorization_header_exposes_super_admin_tools(self):
        app = mcp_asgi_app()
        access = AccessToken(
            token="mango_admin_key",
            client_id="admin",
            subject="1",
            scopes=[],
            claims={"user_id": 1, "is_super_admin": True},
        )

        def httpx_client_factory(**kwargs):
            kwargs.pop("follow_redirects", None)
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://mango-platform.example.com",
                follow_redirects=True,
                **kwargs,
            )

        transport = StreamableHttpTransport(
            "https://mango-platform.example.com/",
            headers={"Authorization": "Bearer mango_admin_key"},
            httpx_client_factory=httpx_client_factory,
        )
        with (
            patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)) as verify_token,
            patch("src.interfaces.mcp.common.get_http_headers", return_value={}),
            patch("src.interfaces.mcp.authentication.bearer_token", return_value=None),
        ):
            async with app.router.lifespan_context(app):
                async with Client(transport) as client:
                    tools = await client.list_tools()

        verify_token.assert_awaited_with("mango_admin_key")
        self.assertGreater(len(tools), 2)
        self.assertIn("list_case_owners", {tool.name for tool in tools})

    async def test_sql_query_removed_from_authenticated_main_and_domain_http_endpoints(self):
        access = AccessToken(token="mango_admin_key", client_id="admin", subject="1", scopes=[],
                             claims={"user_id": 1, "is_super_admin": True})
        for domain in [None, "data-factory"]:
            app = mcp_asgi_app(domain)

            def httpx_client_factory(**kwargs):
                kwargs.pop("follow_redirects", None)
                return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url="https://mango-platform.example.com",
                                         follow_redirects=True, **kwargs)

            transport = StreamableHttpTransport(
                "https://mango-platform.example.com/",
                headers={"Authorization": "Bearer mango_admin_key"},
                httpx_client_factory=httpx_client_factory,
            )
            with (
                self.subTest(domain=domain),
                patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)),
                patch("src.interfaces.mcp.common.get_http_headers", return_value={}),
                patch("src.interfaces.mcp.authentication.bearer_token", return_value=None),
            ):
                async with app.router.lifespan_context(app):
                    async with Client(transport) as client:
                        names = {tool.name for tool in await client.list_tools()}
                        self.assertNotIn("query_data_factory_datasource_sql", names)
                        self.assertIn("get_data_factory_table_schema", names)
                        with self.assertRaises(Exception):
                            await client.call_tool("query_data_factory_datasource_sql", {
                                "sql": "SELECT 1", "datasource_alias_id": 9,
                                "project_product_id": 22, "test_env": 0,
                            })

    async def test_initialize_returns_standard_mcp_session_id(self):
        app = mcp_asgi_app()
        access = AccessToken(
            token="mango_admin_key",
            client_id="admin",
            subject="1",
            scopes=[],
            claims={"user_id": 1, "is_super_admin": True},
        )
        with patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)):
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app),
                        base_url="https://mango-platform.example.com",
                ) as client:
                    response = await client.post(
                        "/",
                        headers={
                            "authorization": "Bearer mango_admin_key",
                            "accept": "application/json, text/event-stream",
                        },
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-11-25",
                                "capabilities": {},
                                "clientInfo": {"name": "apifox", "version": "1.0"},
                            },
                        },
                    )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("mcp-session-id"))
        self.assertEqual(response.json()["result"]["protocolVersion"], "2025-11-25")

    async def test_standard_domain_endpoints_expose_only_their_components(self):
        app = mcp_router_asgi_app()
        access = AccessToken(
            token="mango_admin_key",
            client_id="admin",
            subject="1",
            scopes=[],
            claims={"user_id": 1, "is_super_admin": True},
        )

        def httpx_client_factory(**kwargs):
            kwargs.pop("follow_redirects", None)
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=True,
                **kwargs,
            )

        with patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)):
            async with app.router.lifespan_context(app):
                transport = StreamableHttpTransport(
                    "http://localhost/api",
                    headers={"Authorization": "Bearer mango_admin_key"},
                    httpx_client_factory=httpx_client_factory,
                )
                async with Client(transport) as client:
                    tools = await client.list_tools()
                    static_resources = await client.list_resources()
                    resources = await client.list_resource_templates()
                    prompts = await client.list_prompts()

        names = {tool.name for tool in tools}
        self.assertIn("get_api_case_schema", names)
        self.assertIn("list_project_products", names)
        self.assertNotIn("get_ui_automation_schema", names)
        self.assertNotIn("list_system_files", names)
        self.assertIn(
            "mango://skills/catalog",
            {str(resource.uri) for resource in static_resources},
        )
        self.assertEqual(len(resources), 4)
        self.assertIn("get_mcp_skill_resource", {resource.name for resource in resources})
        self.assertEqual(len(prompts), 3)
        self.assertIn("use_mcp_skill", {prompt.name for prompt in prompts})

    def test_every_documented_domain_endpoint_has_a_server(self):
        app = mcp_router_asgi_app()

        self.assertEqual(set(app.domain_servers), set(MCP_DOMAIN_PATHS))

    def test_token_verifier_logs_and_raises_runtime_errors(self):
        with (
            patch(
                "src.interfaces.mcp.authentication.UserQuerySelector.user"
            ) as user_selector,
            patch("src.interfaces.mcp.authentication.log.system.error") as log_error,
            patch("src.interfaces.mcp.authentication.close_old_connections") as close_connections,
        ):
            user_selector.return_value.select_related.return_value.get.side_effect = RuntimeError(
                "database unavailable")
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                TOKEN_VERIFIER._verify_token_sync("mango_database_error")

        log_error.assert_called_once()
        self.assertEqual(close_connections.call_count, 2)
        self.assertNotIn("mango_database_error", log_error.call_args.args[0])

    async def test_deployed_asgi_route_remains_mcp(self):
        from src.asgi import application, mcp_lifespan_managed_application

        def httpx_client_factory(**kwargs):
            kwargs.pop("follow_redirects", None)
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application),
                base_url="http://localhost",
                follow_redirects=True,
                **kwargs,
            )

        transport = StreamableHttpTransport(
            "http://localhost/mcp",
            headers={"Authorization": "Bearer mango_admin_key"},
            httpx_client_factory=httpx_client_factory,
        )
        access = AccessToken(
            token="mango_admin_key",
            client_id="admin",
            subject="1",
            scopes=[],
            claims={"user_id": 1, "is_super_admin": True},
        )
        try:
            with patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)):
                async with Client(transport) as client:
                    tools = await client.list_tools()
        finally:
            await mcp_lifespan_managed_application.stop()

        self.assertGreater(len(tools), 2)
        self.assertIn("list_project_products", {tool.name for tool in tools})

    async def test_disallowed_host_is_rejected(self):
        app = mcp_asgi_app()

        async def deployed_app(scope, receive, send):
            scope = {**scope, "server": ("127.0.0.1", 8000)}
            await app(scope, receive, send)

        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=deployed_app),
                    base_url="https://untrusted.example.com",
            ) as client:
                response = await client.post(
                    "/",
                    json={},
                    headers={"accept": "application/json, text/event-stream"},
                )

        self.assertEqual(response.status_code, 421)

    @patch("src.interfaces.mcp.authentication.ProjectProductScopeService.has_project_product", return_value=True)
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
           return_value={"api.headers:read"})
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin", return_value=False)
    def test_role_and_department_permission_allow_authorized_project(self, _super_admin, _permissions, _scope):
        user = SimpleNamespace()

        error = permission_error(user, "list_api_headers", {"project_product_id": 12})

        self.assertIsNone(error)

    @patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user", return_value=set())
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin", return_value=False)
    def test_role_permission_denies_missing_page_permission(self, _super_admin, _permissions):
        error = permission_error(SimpleNamespace(), "list_api_headers", {"project_product_id": 12})

        self.assertEqual(error["error_code"], "MCP_PERMISSION_DENIED")

    @patch("src.interfaces.mcp.authentication.ProjectProductScopeService.has_project_product", return_value=False)
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
           return_value={"api.headers:read"})
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin", return_value=False)
    def test_department_scope_denies_unauthorized_project(self, _super_admin, _permissions, _scope):
        error = permission_error(SimpleNamespace(), "list_api_headers", {"project_product_id": 12})

        self.assertEqual(error["error_code"], "MCP_PROJECT_SCOPE_DENIED")

    @patch("src.interfaces.mcp.authentication.resolve_project_product_ids", return_value={1, 2})
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
           return_value={"api.case:add"})
    @patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin", return_value=False)
    def test_cross_project_object_binding_is_rejected(self, _super_admin, _permissions, _resolve):
        error = permission_error(SimpleNamespace(), "add_api_case_step", {"case_id": 1, "api_info_id": 2})

        self.assertEqual(error["error_code"], "MCP_PROJECT_SCOPE_MISMATCH")

    @patch("src.interfaces.mcp.authentication.PermissionMenuService.is_effective_super_admin", return_value=True)
    def test_super_admin_bypasses_role_and_department_checks(self, _super_admin):
        error = permission_error(SimpleNamespace(), "delete_api_case", {"case_id": 999})

        self.assertIsNone(error)

    @patch("src.apps.system.services.configuration.system_config.SystemConfigService.guest_can_view_all_project_data",
           return_value=True)
    def test_guest_global_project_switch_only_applies_to_guest_role(self, _guest_scope):
        guest = SimpleNamespace(role_id=1, role=SimpleNamespace(name="游客"))
        engineer = SimpleNamespace(role_id=2, role=SimpleNamespace(name="自动化工程师"))

        self.assertTrue(ProjectProductScopeService.can_view_all_project_data(guest))
        self.assertFalse(ProjectProductScopeService.can_view_all_project_data(engineer))

    async def test_mango_api_key_is_converted_to_current_user_access_token(self):
        user = SimpleNamespace(id=7, username="tester", role_id=3, is_super_admin=False)
        queryset = MagicMock()
        queryset.get.return_value = user
        with (
            patch("src.interfaces.mcp.authentication.UserQuerySelector.user") as user_selector,
            patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
                  return_value={"api.case:read"}),
        ):
            user_selector.return_value.select_related.return_value = queryset
            access = await MangoTokenVerifier().verify_token("mango_valid_key")

        self.assertEqual(access.subject, "7")
        self.assertEqual(access.client_id, "tester")
        self.assertEqual(access.scopes, ["api.case:read"])

    async def test_invalid_api_key_is_rejected(self):
        queryset = MagicMock()
        queryset.get.side_effect = User.DoesNotExist
        with (
            patch("src.interfaces.mcp.authentication.UserQuerySelector.user") as user_selector,
            patch("src.interfaces.mcp.authentication.close_old_connections") as close_connections,
        ):
            user_selector.return_value.select_related.return_value = queryset
            access = await MangoTokenVerifier().verify_token("mango_invalid_key")

        self.assertIsNone(access)
        self.assertEqual(close_connections.call_count, 2)

    async def test_valid_jwt_is_converted_to_current_user_access_token(self):
        user = SimpleNamespace(id=8, username="jwt_user", role_id=4, is_super_admin=False)
        queryset = MagicMock()
        queryset.get.return_value = user
        with (
            patch("src.interfaces.mcp.authentication.jwt.decode", return_value={"id": 8, "exp": 2000000000}),
            patch("src.interfaces.mcp.authentication.UserQuerySelector.user") as user_selector,
            patch("src.interfaces.mcp.authentication.PermissionMenuService.permission_keys_for_user",
                  return_value={"api.info"}),
        ):
            user_selector.return_value.select_related.return_value = queryset
            access = await MangoTokenVerifier().verify_token("valid.jwt.token")

        self.assertEqual(access.subject, "8")
        self.assertEqual(access.expires_at, 2000000000)

    async def test_expired_jwt_is_rejected(self):
        with patch(
                "src.interfaces.mcp.authentication.jwt.decode",
                side_effect=jwt.ExpiredSignatureError,
        ):
            access = await MangoTokenVerifier().verify_token("expired.jwt.token")

        self.assertIsNone(access)
