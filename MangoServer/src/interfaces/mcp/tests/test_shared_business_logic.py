import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase
from fastmcp import Client
from fastmcp.server.auth import AccessToken

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_case.batch_execution import ApiCaseBatchExecutionService
from src.apps.auto_api.services.api_case.schema import ApiCaseScenarioSchemaService
from src.apps.auto_api.services.api_case.snapshot import ApiCasePublicationState
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_ui.enums import DriveTypeEnum
from src.apps.auto_ui.services.batch_execution import UiCaseBatchExecutionService
from src.apps.auto_ui.services.case_step_cache import UiCaseStepCacheService
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.user.services.environment import UserEnvironmentService
from src.apps.user.services.user_cache import UserCacheService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware
from src.interfaces.mcp.server import mcp_asgi_app
from src.interfaces.mcp.tools.api.case import register_case_tools
from src.interfaces.mcp.tools.api.helpers import _api_case_version_summary


class McpSharedBusinessLogicArchitectureTests(SimpleTestCase):
    FORBIDDEN_MANAGER_METHODS = {
        "create",
        "get_or_create",
        "update_or_create",
        "bulk_create",
        "bulk_update",
        "update",
        "delete",
    }

    def test_mcp_tools_do_not_write_models_directly(self):
        tools_root = Path(__file__).resolve().parents[1] / "tools"
        violations = []
        for path in tools_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if self._is_direct_manager_mutation(node.func):
                    violations.append(f"{path.relative_to(tools_root)}:{node.lineno}")
        self.assertEqual(
            violations,
            [],
            "MCP Tool 不应直接写 ORM，请把业务写操作放入公共 Service：" + ", ".join(violations),
        )

    def _is_direct_manager_mutation(self, func: ast.Attribute) -> bool:
        if func.attr not in self.FORBIDDEN_MANAGER_METHODS:
            return False
        return self._is_manager_chain(func.value)

    def _is_manager_chain(self, node) -> bool:
        if isinstance(node, ast.Attribute):
            return node.attr == "objects" or self._is_manager_chain(node.value)
        if isinstance(node, ast.Call):
            return self._is_manager_chain(node.func)
        return False


class SharedMutationServiceUnitTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        environment_names = patch(
            "src.apps.system.services.system_config.SystemConfigService.get_environment_display_names",
            return_value={},
        )
        environment_names.start()
        self.addCleanup(environment_names.stop)

    @staticmethod
    def _function_source(relative_path: str, function_name: str) -> str:
        path = Path(__file__).resolve().parents[3] / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        return ast.unparse(function)



    def test_api_case_version_summary_preserves_prepublication_state(self):
        state = ApiCasePublicationState(
            publication_status="prepublished",
            current_revision_id=12,
            current_revision_no=2,
            published_release_id=8,
            published_revision_id=10,
            published_version_label="V1",
            prepublished_revision_id=12,
            prepublished_revision_no=2,
            has_unpublished_changes=True,
        )
        with patch.object(
                ApiCaseRevisionService,
                "get_publication_state",
                return_value=state,
        ) as get_state:
            summary = _api_case_version_summary(1)

        get_state.assert_called_once_with(1)
        self.assertEqual(summary, state.to_dict())
        self.assertEqual(summary["publication_status"], "prepublished")
        self.assertEqual(summary["prepublished_revision_id"], 12)

    def test_task_case_ids_are_normalized_once(self):
        self.assertEqual(
            TaskCaseBindingService._normalize_ids(["2", 1, 2, "1"]),
            [2, 1],
        )

    def test_api_case_batch_mcp_uses_shared_execution_service(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        self.assertNotIn("user_id", capture.tools["run_api_case_batch"].__annotations__)
        service_result = {
            "case_ids": [1],
            "executions": [],
            "test_suite_id": 2,
            "execution_name": "回归",
            "test_env": 0,
            "api_concurrency_limit": 1,
            "execution_version": "published",
        }
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution.current_user",
                return_value=SimpleNamespace(id=4),
            ) as current_user,
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution.ApiCaseBatchExecutionService.execute",
                return_value=service_result,
            ) as execute,
        ):
            result = capture.tools["run_api_case_batch"](
                case_ids=[1],
                execution_name="回归",
                test_env_id=0,
                execution_version="published",
            )

        execute.assert_called_once_with(
            case_ids=[1],
            execution_name="回归",
            test_env=0,
            execution_version="published",
            user_id=4,
            api_concurrency_limit=None,
        )
        current_user.assert_called_once_with()
        self.assertTrue(result["success"])

    def test_run_api_case_persists_resolved_release_metadata(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        run_result = {
            "status": 1,
            "error_message": None,
            "trace_id": "trace-1",
            "case_revision_id": 12,
            "case_release_id": 11,
            "version_label": "V2",
        }
        runtime = MagicMock()
        runtime.test_case.return_value.model_dump.return_value = run_result
        execution_result = SimpleNamespace(id=15)
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution.current_user",
                return_value=SimpleNamespace(id=4),
            ),
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution._selected_env",
                return_value=0,
            ),
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution.TestCase",
                return_value=runtime,
            ) as test_case,
            patch(
                "src.interfaces.mcp.tools.api.case_tools.execution.ExecutionResultService.save_result",
                return_value=execution_result,
            ) as save_result,
        ):
            result = capture.tools["run_api_case"](case_id=1, release_id=11)

        test_case.assert_called_once_with(
            user_id=4,
            test_env=0,
            case_id=1,
            trace_source_type=ApiCaseTraceSourceType.MCP,
            revision_id=None,
            release_id=11,
        )
        self.assertEqual(save_result.call_args.kwargs["revision_id"], 12)
        self.assertEqual(save_result.call_args.kwargs["release_id"], 11)
        self.assertEqual(result["data"]["revision_id"], 12)
        self.assertEqual(result["data"]["release_id"], 11)
        self.assertEqual(result["data"]["version_label"], "V2")

    def test_update_api_case_publication_status_submits_prepublication(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        release = SimpleNamespace(
            id=10,
            api_case_id=1,
            revision_id=12,
            version_label="V2",
            is_current=False,
        )
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision."
                "ApiCaseRevisionService.submit_prepublication",
                return_value=release,
            ) as submit,
        ):
            result = capture.tools["update_api_case_publication_status"](
                1,
                "prepublished",
                revision_id=12,
            )

        submit.assert_called_once_with(1, 12)
        self.assertEqual(result["data"], {
            "case_id": 1,
            "revision_id": 12,
            "release_id": 10,
            "status": "prepublished",
            "version_label": "V2",
            "is_current": False,
        })

    def test_update_api_case_publication_status_approves_prepublication(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        release = SimpleNamespace(
            id=11,
            api_case_id=1,
            revision_id=12,
            version_label="V2",
            status="published",
            is_current=True,
        )
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision.current_user",
                return_value=SimpleNamespace(id=4),
            ),
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision."
                "ApiCaseRevisionService.approve_prepublication",
                return_value=release,
            ) as approve,
        ):
            result = capture.tools["update_api_case_publication_status"](1, "published")

        approve.assert_called_once_with(1, operator_id=4)
        self.assertEqual(result["data"], {
            "case_id": 1,
            "revision_id": 12,
            "release_id": 11,
            "version_label": "V2",
            "status": "published",
            "is_current": True,
        })

    def test_update_api_case_publication_status_reverts_prepublication(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        revision = SimpleNamespace(id=12, api_case_id=1)
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision.current_user",
                return_value=SimpleNamespace(id=4),
            ),
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision."
                "ApiCaseRevisionService.revert_prepublication",
                return_value=revision,
            ) as revert,
        ):
            result = capture.tools["update_api_case_publication_status"](1, "unpublished")

        revert.assert_called_once_with(1, operator_id=4)
        self.assertEqual(result["data"], {
            "case_id": 1,
            "revision_id": 12,
            "release_id": None,
            "status": "unpublished",
            "version_label": None,
            "is_current": False,
        })

    def test_update_api_case_publication_status_requires_revision_for_submission(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)

        result = capture.tools["update_api_case_publication_status"](1, "prepublished")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "API_CASE_REVISION_REQUIRED")

    def test_api_case_publication_registers_one_transition_tool(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)

        publication_tools = [name for name in capture.tools if "publication" in name]
        self.assertEqual(publication_tools, ["update_api_case_publication_status"])

    async def test_publish_authorized_client_discovers_one_publication_tool(self):
        access = AccessToken(
            token="mango_api_case_publish_key",
            client_id="api-case-publisher",
            subject="7",
            scopes=["api.case:change"],
            claims={"user_id": 7, "is_super_admin": False},
        )

        with patch.object(
                MangoAuthorizationMiddleware,
                "_access",
                new=AsyncMock(return_value=access),
        ):
            for domain in (None, "api"):
                with self.subTest(domain=domain or "root"):
                    server = mcp_asgi_app(domain).fastmcp_server
                    async with Client(server) as client:
                        tool_names = [tool.name for tool in await client.list_tools()]
                    publication_tools = [name for name in tool_names if "publication" in name]
                    self.assertEqual(publication_tools, ["update_api_case_publication_status"])

    def test_unpublish_api_case_revision_uses_current_release(self):
        class ToolCapture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        capture = ToolCapture()
        register_case_tools(capture)
        current_release = SimpleNamespace(
            id=11,
            api_case_id=1,
            revision_id=12,
            version_label="V2",
            status="published",
            is_current=True,
        )
        unpublished_release = SimpleNamespace(
            id=11,
            api_case_id=1,
            revision_id=12,
            version_label="V2",
            status="deprecated",
            is_current=False,
        )
        with (
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision.current_user",
                return_value=SimpleNamespace(id=4),
            ),
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision."
                "ApiCaseRevisionService.verify_product_owner",
            ) as verify_owner,
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision.ApiQuerySelector.api_case_release"
            ) as release_filter,
            patch(
                "src.interfaces.mcp.tools.api.case_tools.revision.ApiCaseRevisionService.unpublish",
                return_value=unpublished_release,
            ) as unpublish,
        ):
            release_filter.return_value.filter.return_value.first.return_value = current_release
            result = capture.tools["unpublish_api_case_revision"](1, release_id=11, revision_id=12)

        verify_owner.assert_called_once_with(1, 4)
        unpublish.assert_called_once_with(1, 11)
        self.assertEqual(result["data"], {
            "case_id": 1,
            "revision_id": 12,
            "release_id": 11,
            "version_label": "V2",
            "status": "deprecated",
            "is_current": False,
        })

    def test_api_case_batch_http_uses_shared_execution_service(self):
        source = self._function_source(
            "apps/auto_api/api/views/api_case.py",
            "api_test_case_batch",
        )
        self.assertIn("ApiCaseBatchExecutionService.execute", source)
        self.assertNotIn("resolve_release", source)

    def test_api_case_batch_accepts_editing_prepublished_or_published(self):
        self.assertEqual(
            ApiCaseRevisionService.normalize_batch_execution_version("prepublished"),
            "prepublished",
        )
        self.assertEqual(
            ApiCaseRevisionService.normalize_batch_execution_version("editing"),
            "editing",
        )
        self.assertEqual(
            ApiCaseRevisionService.normalize_batch_execution_version("published"),
            "published",
        )
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.normalize_batch_execution_version("release")

    def test_api_case_batch_normalizes_case_ids_once(self):
        self.assertEqual(
            ApiCaseBatchExecutionService.normalize_case_ids(["2", 1]),
            [2, 1],
        )
        with self.assertRaises(AutoApiError):
            ApiCaseBatchExecutionService.normalize_case_ids([1, "1"])

    def test_api_case_batch_shared_service_creates_report_from_selected_mode(self):
        selection = SimpleNamespace(
            case_release_id=11,
            case_revision_id=12,
            case_revision_no=2,
            version_label="V2",
            execution_source="published",
            checksum="checksum",
        )
        case = SimpleNamespace(
            id=1,
            project_product_id=9,
            project_product=SimpleNamespace(
                project_id=8,
                project=SimpleNamespace(id=8, name="测试项目"),
            ),
        )
        queryset = MagicMock()
        queryset.select_related.return_value = [case]
        add_tasks = MagicMock()
        add_tasks.test_suite_id = 13
        with (
            patch(
                "src.apps.auto_api.services.api_case.batch_execution.ApiConcurrencyService.resolve_report_limit",
                return_value=2,
            ),
            patch(
                "src.apps.auto_api.services.api_case.batch_execution.ApiCaseRevisionService.resolve_batch_executions",
                return_value={1: selection},
            ) as resolve,
            patch(
                "src.apps.auto_api.services.api_case.batch_execution.ApiCase.objects.filter",
                return_value=queryset,
            ),
            patch(
                "src.apps.auto_api.services.api_case.batch_execution.AddTasks",
                return_value=add_tasks,
            ) as add_tasks_class,
        ):
            result = ApiCaseBatchExecutionService.execute.__wrapped__(
                ApiCaseBatchExecutionService,
                case_ids=[1],
                execution_name=" 发布态回归 ",
                test_env=0,
                execution_version="published",
                user_id=4,
                api_concurrency_limit=2,
            )

        resolve.assert_called_once_with(
            [1],
            execution_version="published",
            operator_id=4,
        )
        add_tasks_class.assert_called_once_with(
            project_product=9,
            test_env=0,
            is_notice=0,
            user_id=4,
            execution_name="发布态回归",
            api_concurrency_limit=2,
        )
        add_tasks.add_test_suite_details.assert_called_once()
        self.assertEqual(result["test_suite_id"], 13)
        self.assertEqual(result["execution_version"], "published")

    def test_three_shared_workflows_are_used_by_http_and_mcp(self):
        checks = (
            (
                "apps/auto_ui/api/views/ui_case.py",
                "ui_test_case_batch",
                "UiCaseBatchExecutionService.execute",
            ),
            (
                "interfaces/mcp/tools/ui/case.py",
                "run_ui_case_batch",
                "UiCaseBatchExecutionService.execute",
            ),
            (
                "apps/auto_api/api/views/api_case_detailed_parameter.py",
                "put_auto_schema",
                "ApiCaseScenarioSchemaService.generate",
            ),
            (
                "interfaces/mcp/tools/api/scenario.py",
                "auto_generate_api_case_scenario_schema",
                "ApiCaseScenarioSchemaService.generate",
            ),
            (
                "apps/user/api/views/user.py",
                "put_environment",
                "UserEnvironmentService.switch",
            ),
            (
                "interfaces/mcp/tools/project/context.py",
                "switch_user_test_environment",
                "UserEnvironmentService.switch",
            ),
        )
        for relative_path, function_name, shared_call in checks:
            with self.subTest(function=function_name):
                source = self._function_source(relative_path, function_name)
                self.assertIn(shared_call, source)

    def test_ui_step_detail_and_case_cache_use_shared_services(self):
        checks = (
            (
                "apps/auto_ui/api/views/ui_page_steps_detailed.py",
                "post",
                "PageStepDetailMutationService.save",
            ),
            (
                "interfaces/mcp/tools/ui/page_step.py",
                "create_ui_page_step_detail",
                "PageStepDetailMutationService.save",
            ),
            (
                "interfaces/mcp/tools/ui/page_step.py",
                "update_ui_page_step_detail",
                "PageStepDetailMutationService.save",
            ),
            (
                "apps/auto_ui/api/views/ui_case_steps_detailed.py",
                "post_case_cache_data",
                "UiCaseStepCacheService.refresh",
            ),
            (
                "interfaces/mcp/tools/ui/case.py",
                "refresh_ui_case_step_cache_data",
                "UiCaseStepCacheService.refresh",
            ),
        )
        for relative_path, function_name, shared_call in checks:
            with self.subTest(function=function_name):
                source = self._function_source(relative_path, function_name)
                self.assertIn(shared_call, source)

    def test_ui_case_step_cache_uses_flow_execution_order(self):
        details = [
            SimpleNamespace(
                id=10,
                type=3,
                ope_key=None,
                custom=[{"key": "first", "value": "1"}],
                ele_name=None,
                condition_value=None,
            ),
            SimpleNamespace(
                id=20,
                type=3,
                ope_key=None,
                custom=[{"key": "second", "value": "2"}],
                ele_name=None,
                condition_value=None,
            ),
        ]
        queryset = MagicMock()
        queryset.select_related.return_value = list(reversed(details))
        case_step = SimpleNamespace(
            page_step_id=7,
            page_step=SimpleNamespace(
                flow_data={"nodes": [{"config": {"id": 20}}, {"config": {"id": 10}}]}
            ),
        )
        with (
            patch(
                "src.apps.auto_ui.services.case_step_cache.get_execution_order_with_config_ids",
                return_value=[20, 10],
            ),
            patch(
                "src.apps.auto_ui.services.case_step_cache.PageStepsDetailed.objects.filter",
                return_value=queryset,
            ) as detail_filter,
        ):
            result = UiCaseStepCacheService.build_case_data(case_step)

        detail_filter.assert_called_once_with(
            page_step_id=7,
            id__in=[20, 10],
        )
        self.assertEqual(
            [item["page_step_details_id"] for item in result],
            [20, 10],
        )
        self.assertTrue(all(item.get("_source_md5") for item in result))

    def test_ui_case_step_cache_keeps_case_input_when_source_is_unchanged(self):
        source_item = {
            "type": 0,
            "ope_key": "w_input",
            "page_step_details_id": 10,
            "page_step_details_data": [{"f": "text", "v": "页面步骤默认值"}],
            "page_step_details_name": "搜索框",
            "condition_value": None,
        }
        source_item["_source_md5"] = UiCaseStepCacheService.source_md5(source_item)
        current_item = {
            **source_item,
            "page_step_details_data": [{"f": "text", "v": "Case 覆盖值"}],
        }

        result, summary = UiCaseStepCacheService.merge_case_data(
            [current_item],
            [source_item],
        )

        self.assertEqual(
            result[0]["page_step_details_data"][0]["v"],
            "Case 覆盖值",
        )
        self.assertEqual(summary["unchanged_count"], 1)
        self.assertEqual(summary["updated_count"], 0)

    def test_ui_case_step_cache_only_replaces_changed_source_node(self):
        old_source = {
            "type": 0,
            "ope_key": "w_input",
            "page_step_details_id": 10,
            "page_step_details_data": [{"f": "text", "v": "旧默认值"}],
            "page_step_details_name": "搜索框",
            "condition_value": None,
        }
        old_source["_source_md5"] = UiCaseStepCacheService.source_md5(old_source)
        current_item = {
            **old_source,
            "page_step_details_data": [{"f": "text", "v": "Case 覆盖值"}],
        }
        new_source = {
            **old_source,
            "page_step_details_data": [{"f": "text", "v": "新默认值"}],
        }
        new_source["_source_md5"] = UiCaseStepCacheService.source_md5(new_source)

        result, summary = UiCaseStepCacheService.merge_case_data(
            [current_item],
            [new_source],
        )

        self.assertEqual(
            result[0]["page_step_details_data"][0]["v"],
            "新默认值",
        )
        self.assertEqual(summary["updated_count"], 1)
        self.assertEqual(summary["unchanged_count"], 0)

    def test_ui_case_step_cache_initializes_legacy_hash_without_losing_case_input(self):
        source_item = {
            "type": 3,
            "ope_key": None,
            "page_step_details_id": 10,
            "page_step_details_data": [{"key": "name", "value": "页面步骤值"}],
            "page_step_details_name": None,
            "condition_value": None,
        }
        source_item["_source_md5"] = UiCaseStepCacheService.source_md5(source_item)
        legacy_item = {
            key: value
            for key, value in source_item.items()
            if key != "_source_md5"
        }
        legacy_item["page_step_details_data"] = [
            {"key": "name", "value": "Case 值"}
        ]

        result, summary = UiCaseStepCacheService.merge_case_data(
            [legacy_item],
            [source_item],
        )

        self.assertEqual(result[0]["page_step_details_data"][0]["value"], "Case 值")
        self.assertEqual(result[0]["_source_md5"], source_item["_source_md5"])
        self.assertEqual(summary["initialized_count"], 1)

    def test_ui_case_step_cache_adds_removes_and_reorders_nodes(self):
        def source_item(detail_id: int) -> dict:
            item = {
                "type": 3,
                "ope_key": None,
                "page_step_details_id": detail_id,
                "page_step_details_data": [{"key": str(detail_id), "value": "value"}],
                "page_step_details_name": None,
                "condition_value": None,
            }
            item["_source_md5"] = UiCaseStepCacheService.source_md5(item)
            return item

        existing_10 = source_item(10)
        removed_20 = source_item(20)
        added_30 = source_item(30)

        result, summary = UiCaseStepCacheService.merge_case_data(
            [removed_20, existing_10],
            [added_30, existing_10],
        )

        self.assertEqual(
            [item["page_step_details_id"] for item in result],
            [30, 10],
        )
        self.assertEqual(summary["added_count"], 1)
        self.assertEqual(summary["removed_count"], 1)
        self.assertEqual(summary["unchanged_count"], 1)

    def test_ui_run_flow_only_reads_details_from_current_page_step(self):
        queryset = MagicMock()
        queryset.select_related.return_value = []
        with (
            patch(
                "src.apps.auto_ui.services.page_step_detail.get_execution_order_with_config_ids",
                return_value=[11],
            ),
            patch(
                "src.apps.auto_ui.services.page_step_detail.PageStepsDetailed.objects.filter",
                return_value=queryset,
            ) as detail_filter,
        ):
            result = PageStepDetailMutationService.build_run_flow(
                {"nodes": [{"config": {"id": 11}}]},
                page_step_id=7,
            )

        detail_filter.assert_called_once_with(
            id__in=[11],
            page_step_id=7,
        )
        self.assertIsNone(result)

    def test_ui_run_flow_skips_unsaved_nodes_without_detail_id(self):
        queryset = MagicMock()
        queryset.select_related.return_value = []
        with (
            patch(
                "src.apps.auto_ui.services.page_step_detail.get_execution_order_with_config_ids",
                return_value=[None, 11, ""],
            ),
            patch(
                "src.apps.auto_ui.services.page_step_detail.PageStepsDetailed.objects.filter",
                return_value=queryset,
            ) as detail_filter,
        ):
            result = PageStepDetailMutationService.build_run_flow(
                {
                    "nodes": [
                        {"config": {"id": None}},
                        {"config": {"id": 11}},
                    ]
                },
                page_step_id=7,
            )

        detail_filter.assert_called_once_with(
            id__in=[11],
            page_step_id=7,
        )
        self.assertIsNone(result)

    def test_ui_assertion_validation_supports_all_clients_without_page_type(self):
        method = {"value": "w_assert_text", "parameter": []}
        method_tree_data = [
            {
                "value": "ass_web",
                "children": [{"value": "元素断言", "children": [method]}],
            },
            {
                "value": "内容断言",
                "children": [{"value": "p_contains", "parameter": []}],
            },
        ]
        with patch.object(
                PageStepDetailMutationService,
                "cache_method_tree",
                return_value=method_tree_data,
        ) as cache_method_tree:
            method_tree = PageStepDetailMutationService.validation_method_tree(
                "assertion"
            )

        cache_method_tree.assert_called_once_with(
            PageStepDetailMutationService.METHOD_CACHE_KEYS["select_value"]
        )
        self.assertEqual(
            PageStepDetailMutationService.find_method(
                method_tree,
                "w_assert_text",
            ),
            method,
        )

    def test_ui_web_assertion_validation_ignores_android_method_group(self):
        web_method = {"value": "w_page_to_contain_text", "parameter": []}
        android_method = {"value": "a_assert_ele_exists", "parameter": []}
        method_tree_data = [
            {"value": "web", "children": []},
            {"value": "android", "children": []},
            {"value": "ass_web", "children": [web_method]},
            {"value": "ass_android", "children": [android_method]},
            {
                "value": "内容断言",
                "children": [{"value": "p_contains", "parameter": []}],
            },
        ]
        with patch.object(
                PageStepDetailMutationService,
                "cache_method_tree",
                return_value=method_tree_data,
        ):
            method_tree = PageStepDetailMutationService.validation_method_tree(
                "assertion",
                DriveTypeEnum.WEB.value,
            )

        self.assertIsNotNone(
            PageStepDetailMutationService.find_method(
                method_tree,
                "w_page_to_contain_text",
            )
        )
        self.assertIsNone(
            PageStepDetailMutationService.find_method(
                method_tree,
                "a_assert_ele_exists",
            )
        )
        self.assertIsNotNone(
            PageStepDetailMutationService.find_method(
                method_tree,
                "p_contains",
            )
        )

    def test_ui_case_batch_shared_service_creates_one_report(self):
        case = SimpleNamespace(
            id=1,
            project_product_id=9,
            project_product=SimpleNamespace(
                project_id=8,
                project=SimpleNamespace(id=8, name="测试项目"),
            ),
        )
        queryset = MagicMock()
        queryset.select_related.return_value = [case]
        add_tasks = MagicMock(test_suite_id=13)
        with (
            patch(
                "src.apps.auto_ui.services.batch_execution.UiCase.objects.filter",
                return_value=queryset,
            ),
            patch(
                "src.apps.auto_ui.services.batch_execution.AddTasks",
                return_value=add_tasks,
            ) as add_tasks_class,
        ):
            result = UiCaseBatchExecutionService.execute.__wrapped__(
                UiCaseBatchExecutionService,
                case_ids=[1],
                test_env=0,
                user_id=4,
            )

        add_tasks_class.assert_called_once_with(
            project_product=9,
            test_env=0,
            is_notice=0,
            user_id=4,
        )
        add_tasks.add_test_suite_details.assert_called_once()
        self.assertEqual(result["test_suite_id"], 13)

    def test_api_case_schema_shared_service_updates_schema(self):
        parameter = SimpleNamespace(
            id=2,
            case_detailed=SimpleNamespace(case_id=3),
        )
        locked_parameter = SimpleNamespace(
            ass_schema=None,
            update_user_id=None,
            save=MagicMock(),
        )
        manager = MagicMock()
        manager.select_related.return_value.get.return_value = parameter
        manager.select_for_update.return_value.get.return_value = locked_parameter

        def mutate(_case_id, **kwargs):
            return kwargs["operation"](SimpleNamespace())

        with (
            patch(
                "src.apps.auto_api.services.api_case.schema.ApiCaseDetailedParameter.objects",
                manager,
            ),
            patch(
                "src.apps.auto_api.services.api_case.schema.ExecutionResultService.latest_api_case_parameter_result",
                return_value={"response": {"json": {"id": 1}}},
            ),
            patch(
                "src.apps.auto_api.services.api_case.schema.ApiCaseAggregateMutationService.mutate",
                side_effect=mutate,
            ),
        ):
            result = ApiCaseScenarioSchemaService.generate(
                2,
                operator_id=4,
                source="mcp",
            )

        self.assertEqual(result["scenario_id"], 2)
        self.assertEqual(locked_parameter.ass_schema["type"], "object")
        self.assertEqual(locked_parameter.update_user_id, 4)
        locked_parameter.save.assert_called_once()

    def test_user_environment_shared_service_validates_and_saves(self):
        user = SimpleNamespace(
            id=4,
            selected_environment=None,
            config={},
            update_user_id=None,
            save=MagicMock(),
        )
        result = UserEnvironmentService.switch(
            user,
            "0",
            operator_id=4,
        )
        self.assertEqual(result["selected_environment"], 0)
        self.assertEqual(UserCacheService.selected_environment(user), 0)
        user.save.assert_called_once_with(
            update_fields=["config", "update_user", "update_time"]
        )
