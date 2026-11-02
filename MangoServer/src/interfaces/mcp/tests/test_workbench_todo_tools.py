from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from fastmcp import Client
from fastmcp.server.auth import AccessToken

from src.interfaces.mcp.authentication import (
    MangoAuthorizationMiddleware,
    component_policy,
)
from src.interfaces.mcp.registry import domain_registrars
from src.interfaces.mcp.server import _tool_operation, mcp_asgi_app
from src.interfaces.mcp.tools.workbench_todo import register_workbench_todo_tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


class WorkbenchTodoMcpToolTests(SimpleTestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        register_workbench_todo_tools(self.registry)

    def test_tools_are_registered(self):
        self.assertEqual(
            set(self.registry.tools),
            {
                "list_workbench_todos",
                "get_workbench_todo_detail",
                "refresh_workbench_todos",
                "update_workbench_todo_handled",
            },
        )

    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.serialize",
        return_value={"id": 7, "source_id": 31},
    )
    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.summary",
        return_value={"pending": 1},
    )
    @patch("src.interfaces.mcp.tools.workbench_todo.todo._visible_queryset")
    def test_list_todos_filters_and_paginates(self, visible_queryset, summary, serialize):
        todo = SimpleNamespace(id=7)
        queryset = MagicMock()
        queryset.filter.side_effect = lambda **_kwargs: queryset
        queryset.count.return_value = 1
        queryset.__getitem__.return_value = [todo]
        visible_queryset.return_value = queryset

        result = self.registry.tools["list_workbench_todos"](
            status="pending",
            project_product_id=3,
            event_type=6,
            page=1,
            page_size=20,
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["items"], [{"id": 7, "source_id": 31}])
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["page_size"], 20)
        queryset.filter.assert_any_call(project_product_id=3)
        queryset.filter.assert_any_call(event_type=6)
        queryset.filter.assert_any_call(status=0)
        summary.assert_called_once_with(queryset)
        serialize.assert_called_once_with(todo)

    def test_list_todos_rejects_unknown_status(self):
        result = self.registry.tools["list_workbench_todos"](status="unknown")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "WORKBENCH_TODO_STATUS_INVALID")

    @patch("src.interfaces.mcp.tools.workbench_todo.todo._visible_queryset")
    def test_detail_hides_invisible_todo(self, visible_queryset):
        queryset = MagicMock()
        queryset.filter.return_value.first.return_value = None
        visible_queryset.return_value = queryset

        result = self.registry.tools["get_workbench_todo_detail"](todo_id=8)

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "WORKBENCH_TODO_NOT_FOUND")

    def test_manual_handle_requires_evidence_note(self):
        result = self.registry.tools["update_workbench_todo_handled"](
            todo_id=9,
            handle_note=" ",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "WORKBENCH_TODO_HANDLE_NOTE_REQUIRED")

    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.serialize",
        return_value={"id": 9, "status": 1},
    )
    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.mark_handled",
        return_value=True,
    )
    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.can_mark_handled",
        return_value=True,
    )
    @patch("src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.visible_queryset")
    @patch("src.interfaces.mcp.tools.workbench_todo.todo.current_user")
    def test_manual_handle_reuses_service_and_current_user(
            self,
            current_user,
            visible_queryset,
            can_mark_handled,
            mark_handled,
            serialize,
    ):
        user = SimpleNamespace(id=2)
        todo = SimpleNamespace(id=9)
        current_user.return_value = user
        visible_queryset.return_value.filter.return_value.first.return_value = todo

        result = self.registry.tools["update_workbench_todo_handled"](
            todo_id=9,
            handle_note="已线下完成清理并确认无残留",
        )

        self.assertTrue(result["success"], result)
        visible_queryset.assert_called_once_with(user)
        can_mark_handled.assert_called_once_with(todo)
        mark_handled.assert_called_once_with(todo, user, "已线下完成清理并确认无残留")
        serialize.assert_called_once_with(todo)

    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.summary",
        return_value={"pending": 0},
    )
    @patch(
        "src.interfaces.mcp.tools.workbench_todo.todo.WorkbenchTodoService.reconcile_todos",
        return_value={"resolved_auth_todo_count": 1},
    )
    @patch("src.interfaces.mcp.tools.workbench_todo.todo._visible_queryset")
    def test_refresh_returns_reconciliation_and_visible_summary(
            self,
            visible_queryset,
            reconcile_todos,
            summary,
    ):
        queryset = MagicMock()
        visible_queryset.return_value = queryset

        result = self.registry.tools["refresh_workbench_todos"]()

        self.assertTrue(result["success"], result)
        self.assertEqual(result["data"]["summary"], {"pending": 0})
        self.assertEqual(
            result["data"]["reconciliation"],
            {"resolved_auth_todo_count": 1},
        )
        reconcile_todos.assert_called_once_with()
        summary.assert_called_once_with(queryset)

    def test_tools_use_home_permission_and_write_classification(self):
        self.assertEqual(component_policy("list_workbench_todos").permission_key, "index.home")
        self.assertEqual(
            component_policy("update_workbench_todo_handled").permission_key,
            "index.home",
        )
        self.assertEqual(_tool_operation("refresh_workbench_todos"), "execute")
        self.assertEqual(_tool_operation("update_workbench_todo_handled"), "update")
        self.assertEqual(_tool_operation("update_api_case_publication_status"), "update")
        self.assertEqual(_tool_operation("unpublish_api_case_revision"), "update")
        self.assertEqual(
            component_policy("update_api_case_publication_status").permission_key,
            "api.case:change",
        )
        self.assertEqual(domain_registrars("todo")[-1][0], "todo")

    def test_root_and_todo_endpoints_register_todo_tools(self):
        expected_names = set(self.registry.tools)

        for domain in (None, "todo"):
            with self.subTest(domain=domain or "root"):
                server = mcp_asgi_app(domain).fastmcp_server
                tool_names = {
                    tool.name
                    for tool in async_to_sync(server.list_tools)(run_middleware=False)
                }
                self.assertTrue(expected_names.issubset(tool_names))

    async def test_home_authorized_client_can_discover_todo_tools(self):
        expected_names = set(self.registry.tools)
        access = AccessToken(
            token="mango_todo_key",
            client_id="todo-user",
            subject="7",
            scopes=["index.home"],
            claims={"user_id": 7, "is_super_admin": False},
        )

        with patch.object(
                MangoAuthorizationMiddleware,
                "_access",
                new=AsyncMock(return_value=access),
        ):
            for domain in (None, "todo"):
                with self.subTest(domain=domain or "root"):
                    server = mcp_asgi_app(domain).fastmcp_server
                    async with Client(server) as client:
                        tool_names = {tool.name for tool in await client.list_tools()}
                    self.assertTrue(expected_names.issubset(tool_names))
