import json
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase
from fastmcp import Client
from fastmcp.server.auth import AccessToken
from pydantic import ValidationError

from src.apps.auto_api.api.serializers.module_coverage_case import ModuleCoverageCaseSerializer, \
    ModuleCoverageCaseSnapshotSerializer
from src.apps.auto_api.api.serializers.module_coverage_interface import ModuleCoverageInterfaceSerializer, \
    ModuleCoverageInterfaceSnapshotSerializer
from src.apps.auto_api.api.serializers.module_coverage_scan import ModuleCoverageScanSerializer
from src.apps.auto_api.api.views.module_coverage_common import filter_module_scope
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.formatters import MODULE_COVERAGE_DATETIME_FORMAT
from src.apps.auto_api.models import ApiCase, ApiInfo, ApiInfoHttpConfig
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface,
    ModuleCoverageScan,
)
from src.apps.auto_api.schemas.module_coverage import (
    ModuleCoverageCasePayload,
    ModuleCoverageCaseUploadItem,
    ModuleCoverageInterfacePayload,
)
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService
from src.apps.auto_api.services.coverage.module_coverage_diff import build_structured_diff
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.user.models import User
from src.interfaces.mcp.authentication import (
    MangoAuthorizationMiddleware,
    component_policy,
    resolve_project_product_ids,
)
from src.interfaces.mcp.server import _tool_operation, mcp_asgi_app

MODULE_COVERAGE_TOOLS = {
    "create_module_coverage_scan",
    "batch_upsert_module_coverage_interfaces",
    "batch_upsert_module_coverage_cases",
    "get_module_coverage_scan_validation",
    "get_module_coverage_scan_upload_status",
    "get_module_coverage_scan",
    "update_module_coverage_scan",
    "list_module_coverage_scans",
    "list_module_coverage_cases",
    "list_module_coverage_interfaces",
    "get_module_coverage_interface",
    "preview_module_coverage_interface_binding",
    "update_module_coverage_interface_binding",
    "list_module_coverage_interface_snapshots",
    "get_module_coverage_interface_diff",
    "list_module_coverage_interface_cases",
    "get_module_coverage_case",
    "list_module_coverage_case_snapshots",
    "get_module_coverage_case_flow",
    "get_module_coverage_case_diff",
    "update_module_coverage_case_binding",
    "batch_archive_module_coverage_cases",
    "get_module_coverage_metrics",
}


def valid_payload():
    return {
        "interface_source_key": "post:/api/contracts/search",
        "interface_name": "订单列表搜索",
        "method": "POST",
        "url": "/api/contracts/search",
        "case_title": "默认条件查询订单列表",
        "code_evidence": [
            {"path": "src/controller.py", "symbol": "search", "start_line": 10, "end_line": 30},
        ],
        "baseline_commits": [
            {"repository": "backend", "commit_sha": "a" * 40},
        ],
        "test_scenario": "当前身份查询同时包含有权限与无权限订单的数据集",
        "core_assertion": "响应仅包含有权限订单，且不包含无权限订单",
        "scenario_layer": 0,
        "scenario_type": 3,
        "scenario_tags": ["routine_regression"],
        "covered_node_ids": ["request", "auth", "result"],
        "covered_branch_ids": ["authorized"],
    }


def valid_interface_payload():
    return {
        "interface_name": "订单列表搜索",
        "method": "POST",
        "url": "/api/contracts/search",
        "mermaid": """flowchart TD
    request[\"POST /api/contracts/search\"] --> auth{\"有权限?\"}
    auth authorized@-->|是| result([\"返回订单列表\"])
    auth denied@-->|否| denied([\"返回无权限\"])""",
        "node_ids": ["request", "auth", "result", "denied"],
        "branch_ids": ["authorized", "denied"],
    }


class ModuleCoverageSchemaTests(SimpleTestCase):
    def test_inventory_payload_allows_omitted_graph_but_not_orphan_nodes(self):
        payload = {"interface_name": "查询订单", "method": "GET", "url": "/api/contracts"}
        self.assertEqual(ModuleCoverageInterfacePayload.model_validate(payload).node_ids, [])
        for extra in ({"node_ids": ["request"]}, {"gap_reason": "未知"}):
            with self.assertRaises(ValidationError):
                ModuleCoverageInterfacePayload.model_validate({**payload, **extra})

    def test_interface_resolution_distinguishes_placeholder_gap_and_external_boundary(self):
        placeholder = ModuleCoverageService.interface_resolution(
            "flowchart TD\nrequest --> controller --> boundary[\"\u672a\u89e3\u6790\u8fb9\u754c\uff1aController \u540e\u4e1a\u52a1\u94fe\u8def\u5f85\u9010\u63a5\u53e3\u8865\u5145\"]",
            ["request", "controller", "boundary"],
        )
        gap = ModuleCoverageService.interface_resolution(
            "flowchart TD\nrequest --> boundary[\"\u672a\u89e3\u6790\u8fb9\u754c\uff1a\u52a8\u6001\u4ee3理\"]",
            ["request", "boundary"],
        )
        external = ModuleCoverageService.interface_resolution(
            "flowchart TD\nrequest --> boundary[\"\u5916\u90e8\u8fb9\u754c\uff1a\u7b2c\u4e09\u65b9\u7b7e\u7ea6\u670d\u52a1\"]",
            ["request", "boundary"],
        )
        route_only = ModuleCoverageService.interface_resolution(
            "flowchart TD\nrequest --> controller --> boundary[\"未解析边界：动态实现\"]",
            ["request", "controller", "boundary"],
        )

        self.assertEqual(placeholder["status"], "placeholder")
        self.assertEqual(gap["status"], "gap")
        self.assertEqual(external["status"], "resolved")
        self.assertEqual(route_only["status"], "placeholder")

    def test_module_scope_uses_navigation_module_ids(self):
        queryset = MagicMock()
        filtered = MagicMock()
        queryset.filter.return_value = filtered
        request = SimpleNamespace(query_params=QueryDict("module__in=12,13,14&module=12"))

        self.assertIs(filter_module_scope(request, queryset), filtered)
        queryset.filter.assert_called_once_with(module_id__in=[12, 13, 14])

    def test_module_scope_falls_back_to_exact_module(self):
        queryset = MagicMock()
        request = SimpleNamespace(query_params=QueryDict("module=12"))

        filter_module_scope(request, queryset)
        queryset.filter.assert_called_once_with(module_id="12")

    def test_feature_uses_stable_module_interface_relationship_table(self):
        self.assertEqual(
            {
                ModuleCoverageScan._meta.db_table,
                ModuleCoverageCase._meta.db_table,
                ModuleCoverageCaseSnapshot._meta.db_table,
                ModuleCoverageModuleInterface._meta.db_table,
                ModuleCoverageInterfaceSnapshot._meta.db_table,
            },
            {
                "api_module_coverage_scan",
                "api_module_coverage_case",
                "api_module_coverage_case_snapshot",
                "api_module_coverage_module_interface",
                "api_module_coverage_interface_snapshot",
            },
        )
        self.assertTrue(all(model._meta.app_label == "auto_api" for model in (
            ModuleCoverageScan, ModuleCoverageCase, ModuleCoverageCaseSnapshot,
            ModuleCoverageModuleInterface, ModuleCoverageInterfaceSnapshot,
        )))
        self.assertNotIn(
            "automation_decision",
            {field.name for field in ModuleCoverageCase._meta.fields},
        )
        self.assertNotIn(
            "case_no",
            {field.name for field in ModuleCoverageCase._meta.fields},
        )
        self.assertTrue(
            {"scenario_layer", "scenario_type", "scenario_tags"}.issubset(
                {field.name for field in ModuleCoverageCase._meta.fields},
            ),
        )
        self.assertTrue(
            {"gap_reason", "next_action", "resumption_point"}.issubset(
                {field.name for field in ModuleCoverageInterfaceSnapshot._meta.fields},
            ),
        )
        self.assertGreaterEqual(ModuleCoverageScan._meta.get_field("status").max_length, 19)

    def test_payload_accepts_interface_reference_and_coverage_path(self):
        payload = ModuleCoverageCasePayload.model_validate(valid_payload())

        self.assertEqual(payload.interface_source_key, "post:/api/contracts/search")
        self.assertEqual(payload.covered_node_ids, ["request", "auth", "result"])
        self.assertEqual(payload.code_evidence[0].start_line, 10)
        self.assertIn("查询", payload.test_scenario)
        self.assertIn("不包含无权限订单", payload.core_assertion)
        self.assertEqual(payload.scenario_layer, 0)
        self.assertEqual(payload.scenario_type, 3)
        self.assertEqual(payload.scenario_tags, ["routine_regression"])

    def test_payload_requires_valid_case_classification(self):
        for field in ("scenario_layer", "scenario_type", "scenario_tags"):
            with self.subTest(field=field):
                payload = valid_payload()
                payload.pop(field)
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

        for scenario_tags in ([], [""], ["   "]):
            with self.subTest(scenario_tags=scenario_tags):
                payload = valid_payload()
                payload["scenario_tags"] = scenario_tags
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

    def test_case_upload_item_exposes_optional_api_case_binding(self):
        payload = valid_payload()
        payload.update({
            "current_status": "completed",
            "execution_result": "passed",
        })
        item = ModuleCoverageCaseUploadItem.model_validate({
            "source_key": "stable-case-key",
            "payload": payload,
            "api_case_id": 1837,
            "api_case_revision_id": 4576,
        })

        self.assertEqual(item.api_case_id, 1837)
        self.assertEqual(item.api_case_revision_id, 4576)

        for field, value in (
                ("scenario_layer", 3),
                ("scenario_type", 6),
                ("scenario_tags", ["unknown_scene"]),
        ):
            with self.subTest(field=field):
                payload = valid_payload()
                payload[field] = value
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

        payload = valid_payload()
        payload["scenario_tags"] = ["routine_regression", "routine_regression", "smoke_verification"]
        parsed = ModuleCoverageCasePayload.model_validate(payload)
        self.assertEqual(parsed.scenario_tags, ["routine_regression", "smoke_verification"])

    def test_payload_requires_separate_test_scenario_and_core_assertion(self):
        for field in ("test_scenario", "core_assertion"):
            with self.subTest(field=field):
                payload = valid_payload()
                payload.pop(field)
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

        payload = valid_payload()
        payload["scenario_assertion"] = payload.pop("core_assertion")
        with self.assertRaises(ValidationError):
            ModuleCoverageCasePayload.model_validate(payload)

    def test_deferred_payload_requires_reason_and_enablement_condition(self):
        for remark in (None, "", "   "):
            with self.subTest(remark=remark):
                payload = valid_payload()
                payload.update({
                    "current_status": "deferred",
                    "execution_result": "not_applicable",
                    "remark": remark,
                })
                with self.assertRaisesRegex(ValidationError, "payload.remark"):
                    ModuleCoverageCasePayload.model_validate(payload)

        payload = valid_payload()
        payload.update({
            "current_status": "deferred",
            "execution_result": "not_applicable",
            "remark": " 缺少可控时钟；环境支持冻结时间后重新处理。 ",
        })
        parsed = ModuleCoverageCasePayload.model_validate(payload)
        self.assertEqual(parsed.remark, "缺少可控时钟；环境支持冻结时间后重新处理。")

    def test_all_module_coverage_datetime_fields_use_readable_backend_format(self):
        serializer_fields = {
            ModuleCoverageScanSerializer: ("create_time", "update_time", "started_at", "finished_at"),
            ModuleCoverageCaseSerializer: ("create_time", "update_time", "removed_at"),
            ModuleCoverageCaseSnapshotSerializer: ("create_time",),
            ModuleCoverageInterfaceSnapshotSerializer: ("create_time", "removed_at"),
            ModuleCoverageInterfaceSerializer: ("update_time", "removed_at"),
        }
        for serializer_class, field_names in serializer_fields.items():
            with self.subTest(serializer=serializer_class.__name__):
                fields = serializer_class().fields
                for field_name in field_names:
                    self.assertEqual(fields[field_name].format, MODULE_COVERAGE_DATETIME_FORMAT)

    def test_interface_payload_rejects_unknown_or_broken_flow_data(self):
        payload = valid_payload()
        payload["unknown"] = True
        with self.assertRaises(ValidationError):
            ModuleCoverageCasePayload.model_validate(payload)

        for flow in (
                {"nodes": [], "edges": []},
                "sequenceDiagram\nA->>B: request",
                "%%{init: {'theme': 'dark'}}%%\nflowchart TD\nA --> B",
                "flowchart TD\nA --> B\nclick A https://example.com",
        ):
            with self.subTest(flow=flow):
                payload = valid_interface_payload()
                payload["mermaid"] = flow
                with self.assertRaises(ValidationError):
                    ModuleCoverageInterfacePayload.model_validate(payload)

    def test_payload_rejects_values_outside_platform_ledger_contract(self):
        for field, value in (
                ("evidence_category", "Gap"),
                ("evidence_category", "集成测试"),
                ("test_ownership", "其他"),
                ("automation_decision", "automatable"),
                ("current_status", "removed"),
        ):
            with self.subTest(field=field):
                payload = valid_payload()
                payload[field] = value
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

    def test_change_status_only_reflects_scan_result(self):
        active = MagicMock(
            removed_at=None,
            current_snapshot_id=3,
            current_snapshot=MagicMock(sync_action="updated"),
        )
        removed = MagicMock(removed_at=object(), current_snapshot_id=3)

        self.assertEqual(ModuleCoverageCaseSerializer.get_change_status(active), "updated")
        self.assertEqual(ModuleCoverageCaseSerializer.get_change_status(removed), "removed")

    def test_interface_payload_accepts_complete_graph(self):
        payload = ModuleCoverageInterfacePayload.model_validate(valid_interface_payload())

        self.assertTrue(payload.mermaid.startswith("flowchart TD"))
        self.assertEqual(payload.branch_ids, ["authorized", "denied"])

    def test_interface_semantic_hash_ignores_labels_and_layout(self):
        first = valid_interface_payload()
        second = valid_interface_payload()
        second["mermaid"] = (
            'flowchart TD\nrequest["查询入口"] --> auth{"权限判断"}\n'
            'auth authorized@-->|允许| result(["结果"])\n'
            'auth denied@-->|拒绝| denied(["拒绝"])'
        )

        self.assertEqual(
            ModuleCoverageService.interface_semantic_hash(first),
            ModuleCoverageService.interface_semantic_hash(second),
        )

    def test_payload_rejects_invalid_status_combinations(self):
        combinations = [
            ("pending_create", "passed", "HTTP API自动化"),
            ("deferred", "failed", "HTTP API自动化"),
            ("pending_create", "not_executed", "单元测试"),
        ]
        for status, result, ownership in combinations:
            with self.subTest(status=status, result=result, ownership=ownership):
                payload = valid_payload()
                payload.update({
                    "current_status": status,
                    "execution_result": result,
                    "test_ownership": ownership,
                    "remark": "由单元测试负责；出现等价 HTTP 边界后再启用。",
                })
                with self.assertRaises(ValidationError):
                    ModuleCoverageCasePayload.model_validate(payload)

        payload = valid_payload()
        payload.update({
            "current_status": "deferred",
            "execution_result": "not_applicable",
            "test_ownership": "单元测试",
            "remark": "纯函数分支由单元测试负责；出现 HTTP 编排边界后再启用。",
        })
        self.assertEqual(
            ModuleCoverageCasePayload.model_validate(payload).test_ownership,
            "单元测试",
        )

    def test_interface_payload_rejects_orphans_and_missing_branch_ids(self):
        payload = valid_interface_payload()
        payload["node_ids"].append("orphan")
        payload["mermaid"] += '\n    orphan["孤立节点"]'
        with self.assertRaisesRegex(ValidationError, "不可达"):
            ModuleCoverageInterfacePayload.model_validate(payload)

        payload = valid_interface_payload()
        payload["mermaid"] = payload["mermaid"].replace("authorized@", "")
        with self.assertRaisesRegex(ValidationError, "未绑定"):
            ModuleCoverageInterfacePayload.model_validate(payload)

    def test_structured_diff_returns_changed_field_paths(self):
        result = build_structured_diff(
            {"id": 2, "payload": {"test_scenario": "新场景"}, "status": "completed"},
            {"id": 1, "payload": {"test_scenario": "旧场景"}, "status": "completed"},
        )

        self.assertTrue(result["changed"])
        self.assertEqual(result["changed_fields"], ["payload.test_scenario"])


class ModuleCoverageMcpTests(SimpleTestCase):
    @patch.object(ModuleCoverageInterfaceSnapshot.objects, "select_related")
    def test_current_interface_snapshot_reports_stale_id_as_business_error(self, select_related):
        select_related.return_value.get.side_effect = ModuleCoverageInterfaceSnapshot.DoesNotExist

        with self.assertRaises(AutoApiError) as raised:
            ModuleCoverageService.get_current_interface_snapshot(9911)

        self.assertEqual(raised.exception.error_code, "MODULE_COVERAGE_INTERFACE_NOT_FOUND")
        self.assertEqual(raised.exception.details, {"coverage_interface_id": 9911})
        self.assertIn("模块覆盖接口不存在或已失效", raised.exception.msg)

    def test_permissions_and_write_operations_are_classified(self):
        self.assertEqual(
            component_policy("list_module_coverage_cases").permission_key,
            "api.module_coverage",
        )
        self.assertEqual(
            component_policy("batch_upsert_module_coverage_cases").permission_key,
            "api.module_coverage:add",
        )
        self.assertEqual(
            component_policy("batch_upsert_module_coverage_interfaces").permission_key,
            "api.module_coverage:add",
        )
        self.assertEqual(
            component_policy("update_module_coverage_scan").permission_key,
            "api.module_coverage:change",
        )
        self.assertEqual(
            component_policy("preview_module_coverage_interface_binding").permission_key,
            "api.module_coverage",
        )
        self.assertEqual(
            component_policy("update_module_coverage_interface_binding").permission_key,
            "api.module_coverage:change",
        )
        self.assertEqual(_tool_operation("batch_upsert_module_coverage_cases"), "create")
        self.assertEqual(_tool_operation("batch_upsert_module_coverage_interfaces"), "create")
        self.assertEqual(_tool_operation("update_module_coverage_scan"), "update")
        self.assertEqual(_tool_operation("preview_module_coverage_interface_binding"), "read")
        self.assertEqual(_tool_operation("update_module_coverage_interface_binding"), "update")
        self.assertEqual(_tool_operation("batch_archive_module_coverage_cases"), "delete")

    def test_batch_archive_scope_is_resolved_from_coverage_case_ids(self):
        queryset = MagicMock()
        queryset.values_list.return_value.first.return_value = 9
        with patch.object(ModuleCoverageCase.objects, "filter", return_value=queryset):
            project_ids = resolve_project_product_ids(
                "batch_archive_module_coverage_cases",
                {"coverage_case_ids": [11, 12]},
            )

        self.assertEqual(project_ids, {9})

    async def test_authorized_client_discovers_tools_on_root_and_api_endpoints(self):
        access = AccessToken(
            token="mango_module_coverage_key",
            client_id="module-coverage-user",
            subject="7",
            scopes=[
                "api.module_coverage",
                "api.module_coverage:add",
                "api.module_coverage:change",
                "api.module_coverage:remove",
                "api.module_coverage:read",
            ],
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
                        tools = await client.list_tools()
                    names = {tool.name for tool in tools}
                    self.assertTrue(MODULE_COVERAGE_TOOLS.issubset(names))
                    create_scan = next(tool for tool in tools if tool.name == "create_module_coverage_scan")
                    inventory_option = create_scan.inputSchema["properties"]["inventory_only"]
                    self.assertEqual(inventory_option["type"], "boolean")
                    self.assertFalse(inventory_option["default"])
                    case_upload = next(
                        tool for tool in tools
                        if tool.name == "batch_upsert_module_coverage_cases"
                    )
                    self.assertIn("api_case_id", json.dumps(case_upload.inputSchema))
                    self.assertIn("api_case_revision_id", json.dumps(case_upload.inputSchema))
                    schema_text = json.dumps(case_upload.inputSchema, ensure_ascii=False)
                    self.assertIn('"remark"', schema_text)
                    self.assertIn("重新启用条件", schema_text)
                    self.assertIn('"scenario_tags"', schema_text)
                    self.assertIn('"minItems": 1', schema_text)


class ModuleCoverageLifecycleTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name="覆盖扫描测试项目")
        self.product = ProjectProduct.objects.create(project=project, name="后端服务")
        self.module = ProductModule.objects.create(
            project_product=self.product,
            name="订单模块",
            level=1,
        )

    @staticmethod
    def case_item(source_key: str, title: str) -> dict:
        payload = valid_payload()
        payload.update({
            "case_title": title,
            "test_scenario": f"构造并触发{title}对应的请求条件",
            "core_assertion": f"{title}对应的可观察业务结果正确",
        })
        return {"source_key": source_key, "payload": payload}

    @staticmethod
    def interface_item() -> dict:
        return {
            "source_key": "post:/api/contracts/search",
            "payload": valid_interface_payload(),
        }

    def inventory_scan(self, key="inventory", count=1, **overrides):
        return ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "repository_key": "backend", "branch": "main", "commit_sha": "b" * 40,
            "scope_type": "project", "expected_case_count": 0,
            "expected_interface_count": count, "idempotency_key": key, **overrides,
        })

    def inventory_item(self):
        item = self.interface_item()
        for key in ("mermaid", "node_ids", "branch_ids"):
            item["payload"].pop(key)
        return item

    def test_inventory_upload_resume_apply_and_null_module_readback(self):
        scan = self.inventory_scan(count=2)
        item = self.inventory_item()
        ModuleCoverageService.upload_interfaces(scan.id, [item])
        ModuleCoverageService.upload_interfaces(scan.id, [item])
        self.assertFalse(ModuleCoverageService.validation(scan)["valid"])
        conflict = {**item, "payload": {**item["payload"], "interface_name": "冲突名称"}}
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_interfaces(scan.id, [conflict])
        second = {"source_key": "get:/api/contracts", "payload": {
            "interface_name": "查询订单", "method": "GET", "url": "/api/contracts",
        }}
        ModuleCoverageService.upload_interfaces(scan.id, [second])
        status = ModuleCoverageService.upload_status(scan, page=2, page_size=1)
        self.assertEqual(len(status["interface_items"]), 1)
        completed = ModuleCoverageService.complete_scan(scan.id)
        self.assertTrue(completed.summary["applied"])
        self.assertTrue(completed.summary["inventory_only"])
        self.assertEqual(completed.summary["resolved_interface_count"], 0)
        self.assertEqual(ModuleCoverageModuleInterface.objects.count(), 2)
        current = ModuleCoverageInterfaceSnapshot.objects.filter(is_current=True).first()
        detail = ModuleCoverageService.interface_detail(current)
        self.assertIsNone(detail["module"])
        self.assertEqual(detail["resolution_status"], "placeholder")
        page = ModuleCoverageService.interface_page(ModuleCoverageInterfaceSnapshot.objects.all())
        self.assertEqual(page["count"], 2)
        self.assertEqual(len(ModuleCoverageInterfaceSerializer(page["items"], many=True).data), 2)

    def test_inventory_rejects_cases_and_cross_product_module(self):
        with self.assertRaises(AutoApiError):
            self.inventory_scan(expected_case_count=1)
        scan = self.inventory_scan()
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_cases(scan.id, [self.case_item("case1", "订单查询")])
        other = ProjectProduct.objects.create(project=self.product.project, name="其他产品")
        module = ProductModule.objects.create(project_product=other, name="其他模块", level=1)
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_interfaces(scan.id, [{**self.inventory_item(), "module_id": module.id}])
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])

    def test_inventory_preserves_analysis_cases_and_does_not_remove_missing_interfaces(self):
        initial = self.run_scan("a" * 40, [self.case_item("case1", "订单查询")])
        case = ModuleCoverageCase.objects.get(source_key="case1")
        owner = User.objects.create(name="测试负责人", username="inventory-owner", password="pwd")
        api_case = ApiCase.objects.create(
            project_product=self.product, module=self.module, name="订单查询", case_people=owner,
        )
        case.api_case = api_case
        case.status = "completed"
        case.save(update_fields=["api_case", "status"])
        original_case_snapshot = case.current_snapshot_id
        original = initial.interface_snapshots.get()
        scan = self.inventory_scan()
        ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])
        ModuleCoverageService.complete_scan(scan.id)
        relation = ModuleCoverageModuleInterface.objects.get()
        case.refresh_from_db()
        self.assertEqual(relation.current_snapshot_id, original.id)
        self.assertEqual(relation.current_snapshot.scan.commit_sha, "a" * 40)
        self.assertEqual(case.current_snapshot_id, original_case_snapshot)
        self.assertEqual(case.api_case_id, api_case.id)
        self.assertEqual(case.status, "completed")
        self.assertIsNone(case.removed_at)
        empty = self.inventory_scan("empty-inventory", count=0, commit_sha="c" * 40)
        ModuleCoverageService.complete_scan(empty.id)
        relation.refresh_from_db()
        self.assertEqual(relation.current_snapshot_id, original.id)
        self.assertIsNone(relation.removed_at)
        self.assertEqual(ModuleCoverageModuleInterface.objects.count(), 1)

    def test_analysis_after_inventory_reuses_interface_identity(self):
        inventory = self.inventory_scan()
        ModuleCoverageService.upload_interfaces(inventory.id, [self.inventory_item()])
        ModuleCoverageService.complete_scan(inventory.id)
        relation = ModuleCoverageModuleInterface.objects.get()
        analysis = self.run_scan("c" * 40, [self.case_item("case1", "订单查询")])
        relation.refresh_from_db()
        self.assertEqual(ModuleCoverageModuleInterface.objects.count(), 1)
        self.assertEqual(relation.module_id, self.module.id)
        self.assertEqual(relation.current_snapshot.scan_id, analysis.id)
        self.assertEqual(relation.current_snapshot.resolution_status, "resolved")

    def test_module_analysis_still_rejects_empty_graph(self):
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id, "module_id": self.module.id,
            "repository_key": "backend", "branch": "main", "commit_sha": "a" * 40,
            "idempotency_key": "strict-analysis", "expected_case_count": 0, "expected_interface_count": 1,
        })
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])

    def test_module_inventory_preserves_module_without_graph_and_reuses_identity(self):
        scan = self.inventory_scan(scope_type="module", module_id=self.module.id, inventory_only=True)
        ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])
        ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])
        self.assertTrue(ModuleCoverageService.validation(scan)["valid"])
        completed = ModuleCoverageService.complete_scan(scan.id)
        self.assertTrue(completed.summary["inventory_only"])
        relation = ModuleCoverageModuleInterface.objects.get()
        self.assertEqual(relation.module_id, self.module.id)
        self.assertEqual(relation.current_snapshot.module_id, self.module.id)
        self.assertEqual(relation.current_snapshot.node_ids, [])
        self.run_scan("c" * 40, [self.case_item("case1", "订单查询")])
        self.assertEqual(ModuleCoverageModuleInterface.objects.count(), 1)

    def test_module_inventory_cannot_bypass_scope_or_upload_cases(self):
        with self.assertRaises(AutoApiError):
            self.inventory_scan(scope_type="module", inventory_only=True)
        with self.assertRaises(AutoApiError):
            self.inventory_scan(scope_type="module", module_id=self.module.id,
                                inventory_only=True, expected_case_count=1)
        scan = self.inventory_scan(scope_type="module", module_id=self.module.id, inventory_only=True)
        other_module = ProductModule.objects.create(project_product=self.product, name="范围外模块", level=1)
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_interfaces(scan.id, [{**self.inventory_item(), "module_id": other_module.id}])
        with self.assertRaises(AutoApiError):
            ModuleCoverageService.upload_cases(scan.id, [self.case_item("case1", "订单查询")])
        with self.assertRaises(AutoApiError):
            self.inventory_scan(scope_type="module", module_id=self.module.id, inventory_only=False)

    def test_module_inventory_does_not_remove_existing_cases_or_interfaces(self):
        original_scan = self.run_scan("a" * 40, [self.case_item("case1", "订单查询")])
        original = original_scan.interface_snapshots.get()
        scan = self.inventory_scan(scope_type="module", module_id=self.module.id, inventory_only=True)
        ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])
        ModuleCoverageService.complete_scan(scan.id)
        relation = ModuleCoverageModuleInterface.objects.get()
        self.assertEqual(relation.current_snapshot_id, original.id)
        empty = self.inventory_scan("empty-module-inventory", count=0, scope_type="module",
                                    module_id=self.module.id, inventory_only=True, commit_sha="c" * 40)
        ModuleCoverageService.complete_scan(empty.id)
        relation.refresh_from_db()
        case = ModuleCoverageCase.objects.get(source_key="case1")
        self.assertIsNone(case.removed_at)
        self.assertIsNone(relation.removed_at)
        self.assertEqual(relation.current_snapshot_id, original.id)

    def test_module_inventory_is_not_the_analysis_incremental_baseline(self):
        analysis = self.run_scan("a" * 40, [self.case_item("case1", "订单查询")])
        # 历史扫描没有该标识，也必须继续作为分析基线。
        analysis.summary.pop("inventory_only")
        analysis.save(update_fields=["summary"])
        inventory = self.inventory_scan(scope_type="module", module_id=self.module.id, inventory_only=True)
        ModuleCoverageService.upload_interfaces(inventory.id, [self.inventory_item()])
        ModuleCoverageService.complete_scan(inventory.id)
        next_analysis = self.run_scan("c" * 40, [self.case_item("case1", "订单查询")],
                                      mode="incremental", base_commit="a" * 40)
        self.assertEqual(next_analysis.status, "completed")
        increment = self.inventory_scan("incremental-inventory", scope_type="module", module_id=self.module.id,
                                        inventory_only=True, scan_mode="incremental", base_commit_sha="b" * 40,
                                        commit_sha="d" * 40)
        self.assertEqual(increment.base_commit_sha, inventory.commit_sha)

    def test_inventory_rediscovers_removed_route_without_restoring_cases_or_old_graph(self):
        self.run_scan("a" * 40, [self.case_item("case1", "订单查询")])
        self.run_scan("b" * 40, [], confirm_scope_reduction=True)
        scan = self.inventory_scan(commit_sha="c" * 40)
        ModuleCoverageService.upload_interfaces(scan.id, [self.inventory_item()])
        ModuleCoverageService.complete_scan(scan.id)
        relation = ModuleCoverageModuleInterface.objects.get()
        case = ModuleCoverageCase.objects.get(source_key="case1")
        self.assertEqual(relation.lifecycle_status, "active")
        self.assertEqual(relation.current_snapshot.mermaid, "")
        self.assertIsNotNone(case.removed_at)
        self.assertEqual(case.status, "removed")

    def run_scan(
            self,
            commit: str,
            items: list[dict],
            *,
            mode: str = "full",
            base_commit: str | None = None,
            repository_key: str = "backend",
            branch: str = "main",
            confirm_scope_reduction: bool = False,
    ) -> ModuleCoverageScan:
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": repository_key,
            "repository_name": repository_key,
            "branch": branch,
            "commit_sha": commit,
            "base_commit_sha": base_commit,
            "idempotency_key": f"scan-{repository_key}-{branch}-{commit}",
            "expected_case_count": len(items),
            "expected_interface_count": 1 if items else 0,
            "scan_mode": mode,
        })
        if items:
            ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])
            ModuleCoverageService.upload_cases(scan.id, items)
        return ModuleCoverageService.complete_scan(scan.id, confirm_scope_reduction)

    def test_case_can_complete_without_interface_snapshot_and_keeps_ownership(self):
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "a" * 40,
            "idempotency_key": "case-without-interface-snapshot",
            "expected_case_count": 1,
            "expected_interface_count": 0,
            "scan_mode": "incremental",
        })

        ModuleCoverageService.upload_cases(scan.id, [
            self.case_item("case-external-call", "跨产品接口调用场景"),
        ])
        completed = ModuleCoverageService.complete_scan(scan.id)

        coverage_case = ModuleCoverageCase.objects.get(source_key="case-external-call")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(coverage_case.project_product_id, self.product.id)
        self.assertEqual(coverage_case.module_id, self.module.id)
        self.assertIsNone(coverage_case.module_interface_id)
        self.assertIsNone(coverage_case.current_snapshot.interface_snapshot_id)
        self.assertEqual(coverage_case.coverage_validity, "pending_review")
        self.assertIn("不影响Case归属和接口调用", coverage_case.coverage_validity_reason)

    def test_repeated_full_scan_tracks_create_update_remove_and_restore(self):
        first_commit = "1" * 40
        second_commit = "2" * 40
        third_commit = "3" * 40
        first = self.run_scan(first_commit, [
            self.case_item("case-a", "场景A"),
            self.case_item("case-b", "场景B"),
            self.case_item("case-c", "场景C"),
        ])
        self.assertEqual(first.summary["created"], 3)
        self.assertEqual(first.summary["removed"], 0)
        self.assertEqual(first.summary["interface_created"], 1)
        self.assertEqual(first.schema_version, 3)
        first_case = ModuleCoverageCase.objects.get(source_key="case-a")
        self.assertEqual(first_case.interface_source_key, "post:/api/contracts/search")

        second = self.run_scan(second_commit, [
            self.case_item("case-a", "场景A"),
            self.case_item("case-b", "场景B已修改"),
            self.case_item("case-d", "场景D"),
        ])
        self.assertEqual(second.summary["created"], 1)
        self.assertEqual(second.summary["updated"], 1)
        self.assertEqual(second.summary["unchanged"], 1)
        self.assertEqual(second.summary["removed"], 1)
        self.assertEqual(second.summary["interface_unchanged"], 1)
        removed = ModuleCoverageCase.objects.get(source_key="case-c")
        self.assertIsNotNone(removed.removed_at)

        third = self.run_scan(
            third_commit,
            [self.case_item("case-c", "场景C")],
            mode="incremental",
            base_commit=second_commit,
        )
        self.assertEqual(third.summary["removed"], 0)
        removed.refresh_from_db()
        self.assertIsNone(removed.removed_at)
        self.assertEqual(ModuleCoverageService.active_cases(self.product.id, self.module.id).count(), 4)

    def test_placeholder_interface_blocks_scan_completion(self):
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "9" * 40,
            "idempotency_key": "scan-placeholder-flow",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "full",
        })
        payload = valid_interface_payload()
        payload.update({
            "mermaid": (
                "flowchart TD\n"
                "    request[\"POST /api/contracts/search\"] --> controller[\"Controller.search\"]\n"
                "    controller --> boundary[\"\u672a\u89e3\u6790\u8fb9\u754c\uff1aController \u540e\u4e1a\u52a1\u94fe\u8def\u5f85\u9010\u63a5口补充\"]"
            ),
            "node_ids": ["request", "controller", "boundary"],
            "branch_ids": [],
        })
        ModuleCoverageService.upload_interfaces(scan.id, [{
            "source_key": "post:/api/contracts/search",
            "payload": payload,
        }])

        validation = ModuleCoverageService.validation(scan)
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["placeholder_interface_count"], 1)
        self.assertEqual(validation["resolved_interface_count"], 0)
        with self.assertRaisesMessage(AutoApiError, "\u5360\u4f4d1个"):
            ModuleCoverageService.complete_scan(scan.id)

        scan.refresh_from_db()
        self.assertEqual(scan.status, "uploading")

    def test_gap_scan_can_close_as_audit_without_applying_assets(self):
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "8" * 40,
            "idempotency_key": "scan-with-structured-gap",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "full",
        })
        payload = valid_interface_payload()
        payload.update({
            "mermaid": (
                "flowchart TD\n"
                "    request[\"POST /api/contracts/search\"] --> boundary[\"未解析边界：运行期动态代理\"]"
            ),
            "node_ids": ["request", "boundary"],
            "branch_ids": [],
            "gap_reason": "代理实现由运行期配置选择，当前仓库无法确定目标类",
            "next_action": "提供测试环境代理映射后继续追踪",
            "resumption_point": "ContractProxyFactory.resolve",
        })
        ModuleCoverageService.upload_interfaces(scan.id, [{
            "source_key": "post:/api/contracts/search",
            "payload": payload,
        }])

        validation = ModuleCoverageService.validation(scan)
        self.assertFalse(validation["valid"])
        self.assertTrue(validation["valid_with_gaps"])
        completed = ModuleCoverageService.complete_scan_with_gaps(scan.id)

        self.assertEqual(completed.status, "completed_with_gaps")
        self.assertFalse(completed.summary["applied"])
        self.assertFalse(completed.interface_snapshots.get().is_current)

    def test_incremental_scan_does_not_remove_omitted_cases(self):
        first_commit = "4" * 40
        second_commit = "5" * 40
        self.run_scan(first_commit, [
            self.case_item("case-a", "场景A"),
            self.case_item("case-b", "场景B"),
        ])
        scan = self.run_scan(
            second_commit,
            [self.case_item("case-a", "场景A已修改")],
            mode="incremental",
            base_commit=first_commit,
        )

        self.assertEqual(scan.summary["updated"], 1)
        self.assertEqual(scan.summary["removed"], 0)
        self.assertIsNone(ModuleCoverageCase.objects.get(source_key="case-b").removed_at)

    def test_interface_view_uses_interface_snapshot_and_keeps_case_highlight_nodes(self):
        first = self.case_item("case-a", "有权限场景")
        second = self.case_item("case-b", "无权限场景")
        second["payload"]["covered_node_ids"] = ["request", "auth", "denied"]
        second["payload"]["covered_branch_ids"] = ["denied"]
        self.run_scan("b" * 40, [first, second])

        queryset = ModuleCoverageService.active_cases(
            self.product.id,
            self.module.id,
            "backend",
            "main",
        )
        coverage_interface = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        page = ModuleCoverageService.interface_page(
            ModuleCoverageInterfaceSnapshot.objects.select_related("scan").all(),
        )
        self.assertEqual(page["count"], 1)
        self.assertEqual(page["items"][0]["case_count"], 2)
        self.assertEqual(page["items"][0]["resolution_status"], "resolved")

        detail = ModuleCoverageService.interface_detail(coverage_interface, queryset)
        self.assertEqual(detail["case_count"], 2)
        self.assertEqual(detail["mermaid"], valid_interface_payload()["mermaid"])
        self.assertEqual(detail["resolution_status"], "resolved")
        self.assertIn("denied", detail["mermaid"])
        self.assertEqual(
            {item["name"] for item in detail["cases"]},
            {"有权限场景", "无权限场景"},
        )
        self.assertIn("denied", detail["cases"][1]["node_ids"])

    def test_metrics_are_isolated_by_repository_and_branch(self):
        self.run_scan("6" * 40, [self.case_item("main-case", "主分支场景")])
        self.run_scan(
            "7" * 40,
            [self.case_item("feature-case", "特性分支场景")],
            branch="feature/module-coverage",
        )
        self.run_scan(
            "8" * 40,
            [self.case_item("worker-case", "异步仓库场景")],
            repository_key="worker",
        )

        self.assertEqual(
            ModuleCoverageService.metrics(
                self.product.id,
                self.module.id,
                "backend",
                "main",
            )["case_total"],
            1,
        )
        self.assertEqual(
            ModuleCoverageService.metrics(self.product.id, self.module.id)["case_total"],
            3,
        )

    def test_current_status_drives_automation_metrics_and_binding_progress(self):
        self.run_scan("c" * 40, [self.case_item("case-status", "状态合并场景")])
        coverage_case = ModuleCoverageCase.objects.get(source_key="case-status")
        metrics = ModuleCoverageService.metrics(self.product.id, self.module.id)
        self.assertEqual(coverage_case.status, "pending_create")
        self.assertEqual(metrics["target_case_count"], 1)
        self.assertEqual(metrics["pending_case_count"], 1)
        self.assertEqual(metrics["deferred_case_count"], 0)
        self.assertEqual(metrics["resolved_interface_count"], 1)
        self.assertEqual(metrics["placeholder_interface_count"], 0)
        self.assertEqual(metrics["interface_resolution_rate"], 100)

        coverage_case.status = "deferred"
        coverage_case.save(update_fields=["status"])
        metrics = ModuleCoverageService.metrics(self.product.id, self.module.id)
        self.assertEqual(metrics["target_case_count"], 0)
        self.assertEqual(metrics["pending_case_count"], 0)
        self.assertEqual(metrics["deferred_case_count"], 1)

        owner = User.objects.create(
            name="模块覆盖负责人",
            username="module_coverage_owner",
            password="pwd",
        )
        api_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name="模块覆盖绑定用例",
            case_people=owner,
        )
        bound = ModuleCoverageService.bind_api_case(coverage_case.id, api_case.id)
        self.assertEqual(bound.status, "completed")
        metrics = ModuleCoverageService.metrics(self.product.id, self.module.id)
        self.assertEqual(metrics["target_case_count"], 1)
        self.assertEqual(metrics["pending_case_count"], 0)
        self.assertEqual(metrics["completed_case_count"], 1)
        self.assertEqual(metrics["effective_completed_case_count"], 1)
        self.assertEqual(metrics["effective_coverage_rate"], 100)
        self.assertEqual(metrics["deferred_case_count"], 0)

    def test_binding_backfills_latest_execution_and_future_execution_syncs(self):
        self.run_scan("7" * 40, [self.case_item("case-execution-sync", "执行结果同步场景")])
        coverage_case = ModuleCoverageCase.objects.get(source_key="case-execution-sync")
        owner = User.objects.create(
            name="执行同步负责人",
            username="module_coverage_execution_sync_owner",
            password="pwd",
        )
        api_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name="执行同步用例",
            case_people=owner,
        )
        with patch.object(
                ExecutionResultService,
                "prepare_result_payload",
                return_value={
                    "result_data": {"status": 1},
                    "result_object_key": None,
                    "result_file_name": None,
                    "result_size": 12,
                    "result_checksum": "checksum",
                },
        ):
            ExecutionResultService.save_result(
                source_type=ExecutionResultService.SOURCE_MCP,
                target_type=ExecutionResultService.TARGET_API_CASE,
                target_id=api_case.id,
                status=1,
                result_data={"status": 1},
            )

        ModuleCoverageService.bind_api_case(coverage_case.id, api_case.id)
        coverage_case.refresh_from_db()
        self.assertEqual(coverage_case.execution_result, "passed")

        with patch.object(
                ExecutionResultService,
                "prepare_result_payload",
                return_value={
                    "result_data": {"status": 0},
                    "result_object_key": None,
                    "result_file_name": None,
                    "result_size": 12,
                    "result_checksum": "checksum",
                },
        ):
            ExecutionResultService.save_result(
                source_type=ExecutionResultService.SOURCE_MCP,
                target_type=ExecutionResultService.TARGET_API_CASE,
                target_id=api_case.id,
                status=0,
                result_data={"status": 0},
            )

        coverage_case.refresh_from_db()
        self.assertEqual(coverage_case.execution_result, "failed")

    def test_api_entry_rate_only_counts_current_interface_identities(self):
        self.run_scan("8" * 40, [self.case_item("case-entry-scope", "接口录入统计场景")])
        coverage_case = ModuleCoverageCase.objects.get(source_key="case-entry-scope")
        owner = User.objects.create(
            name="接口统计负责人",
            username="module_coverage_entry_scope_owner",
            password="pwd",
        )
        api_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name="接口录入统计用例",
            case_people=owner,
        )
        ModuleCoverageService.bind_api_case(coverage_case.id, api_case.id)
        coverage_case.interface_source_key = "post:/api/removed"
        coverage_case.interface_source_key_hash = "f" * 64
        coverage_case.save(update_fields=["interface_source_key", "interface_source_key_hash"])

        metrics = ModuleCoverageService.metrics(self.product.id, self.module.id)

        self.assertEqual(metrics["api_total"], 1)
        self.assertEqual(metrics["entered_api_total"], 0)
        self.assertEqual(metrics["api_entry_rate"], 0)

    def test_upload_rejects_status_and_api_case_binding_mismatch(self):
        owner = User.objects.create(
            name="模块覆盖协议负责人",
            username="module_coverage_contract_owner",
            password="pwd",
        )
        api_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name="模块覆盖协议用例",
            case_people=owner,
        )
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "d" * 40,
            "idempotency_key": "scan-status-binding-contract",
            "expected_case_count": 1,
            "expected_interface_count": 1,
            "scan_mode": "full",
        })
        ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])

        pending_with_binding = self.case_item("case-binding-mismatch", "状态绑定不一致")
        pending_with_binding["api_case_id"] = api_case.id
        with self.assertRaisesMessage(AutoApiError, "current_status=completed"):
            ModuleCoverageService.upload_cases(scan.id, [pending_with_binding])

        completed_without_binding = self.case_item("case-binding-mismatch", "状态绑定不一致")
        completed_without_binding["payload"]["current_status"] = "completed"
        with self.assertRaisesMessage(AutoApiError, "current_status=completed"):
            ModuleCoverageService.upload_cases(scan.id, [completed_without_binding])

    def test_metrics_support_all_projects_and_keep_urls_product_scoped(self):
        self.run_scan("9" * 40, [self.case_item("primary-case", "主产品场景")])
        primary_product = self.product
        primary_module = self.module
        other_product = ProjectProduct.objects.create(
            project=primary_product.project,
            name="另一个后端服务",
        )
        other_module = ProductModule.objects.create(
            project_product=other_product,
            name="订单模块",
            level=1,
        )
        self.product = other_product
        self.module = other_module
        try:
            self.run_scan("a" * 40, [self.case_item("other-case", "其他产品场景")])
        finally:
            self.product = primary_product
            self.module = primary_module

        metrics = ModuleCoverageService.metrics()
        self.assertEqual(metrics["case_total"], 2)
        self.assertEqual(metrics["api_total"], 2)

        scoped_metrics = ModuleCoverageService.metrics(
            case_queryset=ModuleCoverageCase.objects.filter(project_product=primary_product),
            scan_queryset=ModuleCoverageScan.objects.filter(project_product=primary_product),
        )
        self.assertEqual(scoped_metrics["case_total"], 1)

    def test_single_interface_incremental_scan_marks_omitted_case_invalid(self):
        first_commit = "e" * 40
        second_commit = "f" * 40
        self.run_scan(first_commit, [self.case_item("case-path", "接口路径场景")])
        target = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": second_commit,
            "base_commit_sha": first_commit,
            "idempotency_key": "single-interface-incremental",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "incremental",
            "scope_type": "interface",
            "target_interface_id": target.id,
        })
        payload = valid_interface_payload()
        payload.update({
            "mermaid": "flowchart TD\nrequest[\"POST /api/contracts/search\"] --> result([\"返回订单列表\"])",
            "node_ids": ["request", "result"],
            "branch_ids": [],
        })
        ModuleCoverageService.upload_interfaces(scan.id, [{
            "source_key": "post:/api/contracts/search",
            "payload": payload,
        }])
        ModuleCoverageService.complete_scan(scan.id)

        coverage_case = ModuleCoverageCase.objects.get(source_key="case-path")
        self.assertEqual(coverage_case.status, "pending_create")
        self.assertEqual(coverage_case.coverage_validity, "invalid")
        self.assertIn("auth", coverage_case.coverage_validity_reason)
        self.assertEqual(coverage_case.interface_source_key_hash, target.source_key_hash)

    def test_single_interface_upload_uses_bound_target_when_legacy_currents_are_duplicated(self):
        self.run_scan("a" * 40, [self.case_item("case-legacy", "历史接口场景")])
        self.run_scan(
            "b" * 40,
            [self.case_item("case-legacy", "历史接口场景")],
            mode="incremental",
            base_commit="a" * 40,
        )
        snapshots = list(ModuleCoverageInterfaceSnapshot.objects.order_by("id"))
        legacy, target = snapshots[0], snapshots[1]
        legacy.is_current = True
        legacy.save(update_fields=["is_current"])

        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "c" * 40,
            "base_commit_sha": "b" * 40,
            "idempotency_key": "single-interface-duplicate-current",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "incremental",
            "scope_type": "interface",
            "target_interface_id": target.id,
        })

        result = ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])

        self.assertEqual(result["accepted"], 1)
        self.assertEqual(scan.interface_snapshots.get().sync_action, "unchanged")

    def test_module_upload_ignores_stale_legacy_current_flag(self):
        self.run_scan("d" * 40, [self.case_item("case-duplicate", "重复当前接口场景")])
        self.run_scan(
            "e" * 40,
            [self.case_item("case-duplicate", "重复当前接口场景")],
            mode="incremental",
            base_commit="d" * 40,
        )
        legacy = ModuleCoverageInterfaceSnapshot.objects.order_by("id").first()
        legacy.is_current = True
        legacy.save(update_fields=["is_current"])
        current_snapshot_id = ModuleCoverageModuleInterface.objects.get(
            module=self.module,
            repository_key="backend",
            branch="main",
        ).current_snapshot_id
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "f" * 40,
            "base_commit_sha": "e" * 40,
            "idempotency_key": "module-duplicate-current",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "incremental",
        })

        result = ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])

        self.assertEqual(result["accepted"], 1)
        self.assertEqual(
            scan.interface_snapshots.get().module_interface.current_snapshot_id,
            current_snapshot_id,
        )

    def test_backfill_repairs_duplicate_current_only_when_explicitly_requested(self):
        self.run_scan("1" * 40, [self.case_item("case-repair", "重复快照修复场景")])
        self.run_scan(
            "2" * 40,
            [self.case_item("case-repair", "重复快照修复场景")],
            mode="incremental",
            base_commit="1" * 40,
        )
        snapshots = list(ModuleCoverageInterfaceSnapshot.objects.order_by("id"))
        snapshots[0].is_current = True
        snapshots[0].save(update_fields=["is_current"])

        with self.assertRaises(CommandError):
            call_command("backfill_module_coverage_snapshot_links", stdout=StringIO())

        call_command(
            "backfill_module_coverage_snapshot_links",
            "--execute",
            "--repair-duplicate-current",
            "--only-duplicate-current",
            stdout=StringIO(),
        )

        current = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        self.assertEqual(current.id, snapshots[1].id)

    def test_single_interface_scan_does_not_remove_owned_case_when_omitted(self):
        self.run_scan("1" * 40, [self.case_item("case-target", "目标接口场景")])
        target = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "2" * 40,
            "idempotency_key": "single-interface-full",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "full",
            "scope_type": "interface",
            "target_interface_id": target.id,
        })
        ModuleCoverageService.upload_interfaces(scan.id, [self.interface_item()])
        completed = ModuleCoverageService.complete_scan(scan.id, confirm_scope_reduction=True)

        target.refresh_from_db()
        coverage_case = ModuleCoverageCase.objects.get(source_key="case-target")
        self.assertEqual(completed.summary["interface_removed"], 0)
        self.assertTrue(ModuleCoverageInterfaceSnapshot.objects.filter(
            source_key_hash=target.source_key_hash,
            is_current=True,
            lifecycle_status="active",
        ).exists())
        self.assertNotEqual(coverage_case.status, "removed")
        self.assertIsNone(coverage_case.removed_at)

    def test_module_full_scan_marks_missing_interface_and_cases_removed(self):
        self.run_scan("3" * 40, [self.case_item("case-removed", "接口移除场景")])
        target = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        scan = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": self.module.id,
            "repository_key": "backend",
            "repository_name": "backend",
            "branch": "main",
            "commit_sha": "4" * 40,
            "idempotency_key": "module-interface-removal",
            "expected_case_count": 0,
            "expected_interface_count": 0,
            "scan_mode": "full",
        })
        completed = ModuleCoverageService.complete_scan(scan.id, confirm_scope_reduction=True)

        coverage_case = ModuleCoverageCase.objects.get(source_key="case-removed")
        self.assertEqual(completed.summary["interface_removed"], 1)
        target.refresh_from_db()
        self.assertFalse(target.is_current)
        self.assertTrue(ModuleCoverageInterfaceSnapshot.objects.filter(
            source_key_hash=target.source_key_hash,
            is_current=True,
            lifecycle_status="removed",
        ).exists())
        self.assertEqual(coverage_case.status, "removed")

    def test_interface_move_keeps_stable_interface_identity(self):
        root = ProductModule.objects.create(
            project_product=self.product,
            name="服务模块",
            level=1,
        )
        first_module = ProductModule.objects.create(
            project_product=self.product,
            name="旧模块",
            level=2,
            parent=root,
        )
        second_module = ProductModule.objects.create(
            project_product=self.product,
            name="新模块",
            level=2,
            parent=root,
        )
        scan1 = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": root.id,
            "include_descendants": True,
            "repository_key": "move-backend",
            "repository_name": "move-backend",
            "branch": "main",
            "commit_sha": "5" * 40,
            "idempotency_key": "module-move-first",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "full",
        })
        item = self.interface_item()
        item["module_id"] = first_module.id
        ModuleCoverageService.upload_interfaces(scan1.id, [item])
        ModuleCoverageService.complete_scan(scan1.id)
        stable_hash = ModuleCoverageInterfaceSnapshot.objects.get(
            repository_key="move-backend", is_current=True,
        ).source_key_hash

        scan2 = ModuleCoverageService.create_scan({
            "project_product_id": self.product.id,
            "module_id": root.id,
            "include_descendants": True,
            "repository_key": "move-backend",
            "repository_name": "move-backend",
            "branch": "main",
            "commit_sha": "6" * 40,
            "idempotency_key": "module-move-second",
            "expected_case_count": 0,
            "expected_interface_count": 1,
            "scan_mode": "full",
        })
        moved = self.interface_item()
        moved["module_id"] = second_module.id
        ModuleCoverageService.upload_interfaces(scan2.id, [moved])
        ModuleCoverageService.complete_scan(scan2.id)

        snapshots = ModuleCoverageInterfaceSnapshot.objects.filter(
            repository_key="move-backend", source_key_hash=stable_hash,
        )
        self.assertEqual(snapshots.count(), 2)
        self.assertEqual(
            snapshots.get(is_current=True, lifecycle_status="active").module_id,
            second_module.id,
        )
        self.assertEqual(ModuleCoverageModuleInterface.objects.filter(
            repository_key="move-backend",
            source_key_hash=stable_hash,
        ).count(), 2)

    def test_interface_snapshot_can_bind_api_info_owned_by_another_module(self):
        owner_module = ProductModule.objects.create(
            project_product=self.product,
            name="接口资产模块",
            level=1,
        )
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=owner_module,
            name="订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=api_info,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )

        self.run_scan("0" * 40, [self.case_item("case-cross-module", "跨模块复用场景")])

        relation = ModuleCoverageModuleInterface.objects.get(module=self.module)
        self.assertEqual(relation.api_info_id, api_info.id)
        self.assertEqual(relation.api_info.module_id, owner_module.id)
        self.assertNotEqual(relation.module_id, relation.api_info.module_id)

    def test_interface_snapshot_reuses_existing_api_info_without_creating_duplicate(self):
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name="订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=api_info,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )

        self.run_scan("7" * 40, [self.case_item("case-api-info", "ApiInfo绑定场景")])

        interface = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        self.assertEqual(interface.api_info_id, api_info.id)
        self.assertEqual(interface.api_info_binding_status, "bound")
        self.assertEqual(ApiInfo.objects.count(), 1)
        metrics = ModuleCoverageService.metrics(
            project_product_id=self.product.id,
            module_id=self.module.id,
            repository_key="backend",
            branch="main",
        )
        self.assertEqual(metrics["bound_api_info_count"], 1)
        self.assertEqual(metrics["unbound_api_info_count"], 0)
        self.assertEqual(metrics["api_info_binding_rate"], 100)

    def test_interface_binding_correction_creates_auditable_incremental_snapshot(self):
        self.run_scan("6" * 40, [self.case_item("case-binding-correction", "绑定修正场景")])
        original = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        owner_module = ProductModule.objects.create(
            project_product=self.product,
            name="接口Owner模块",
            level=1,
        )
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=owner_module,
            name="订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=api_info,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )

        preview = ModuleCoverageService.preview_interface_binding_correction(
            original.id,
            api_info.id,
        )
        result = ModuleCoverageService.update_interface_binding(original.id, api_info.id)

        original.refresh_from_db()
        relation = ModuleCoverageModuleInterface.objects.get(module=self.module)
        self.assertTrue(preview["changed"])
        self.assertFalse(preview["history_snapshot_mutated"])
        self.assertFalse(preview["api_info_owner_mutated"])
        self.assertTrue(result["applied"])
        self.assertNotEqual(result["new_coverage_interface_id"], original.id)
        self.assertFalse(original.is_current)
        self.assertIsNone(original.api_info_id)
        self.assertEqual(relation.api_info_id, api_info.id)
        self.assertEqual(relation.api_info.module_id, owner_module.id)
        self.assertEqual(relation.module_id, self.module.id)
        self.assertEqual(relation.current_snapshot.scan.scope_type, "interface")
        self.assertEqual(relation.current_snapshot.scan.scan_mode, "incremental")

    def test_interface_binding_correction_is_idempotent(self):
        self.run_scan("5" * 40, [self.case_item("case-binding-idempotent", "幂等绑定修正")])
        original = ModuleCoverageInterfaceSnapshot.objects.get(is_current=True)
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name="订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=api_info,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )

        first = ModuleCoverageService.update_interface_binding(original.id, api_info.id)
        current_id = first["new_coverage_interface_id"]
        scan_count = ModuleCoverageScan.objects.count()
        snapshot_count = ModuleCoverageInterfaceSnapshot.objects.count()
        second = ModuleCoverageService.update_interface_binding(original.id, api_info.id)

        self.assertFalse(second["applied"])
        self.assertEqual(second["new_coverage_interface_id"], current_id)
        self.assertEqual(ModuleCoverageScan.objects.count(), scan_count)
        self.assertEqual(ModuleCoverageInterfaceSnapshot.objects.count(), snapshot_count)

    def test_rescan_preserves_existing_binding_when_duplicate_candidates_exist(self):
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name="订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=api_info,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )
        self.run_scan("7" * 40, [self.case_item("case-original-binding", "原绑定场景")])

        duplicate_module = ProductModule.objects.create(
            project_product=self.product,
            name="重复接口模块",
            level=1,
        )
        duplicate = ApiInfo.objects.create(
            project_product=self.product,
            module=duplicate_module,
            name="重复订单列表搜索",
            url="/api/contracts/search",
            posterior_json_path=[],
            posterior_re=[],
            status=2,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=duplicate,
            method=1,
            url="/api/contracts/search",
            headers=None,
            params=None,
            is_text_params=1,
            body_type="none",
            body_config=None,
            sse_config=None,
        )

        self.run_scan("8" * 40, [self.case_item("case-original-binding", "原绑定场景")])

        relation = ModuleCoverageModuleInterface.objects.get(module=self.module)
        self.assertEqual(relation.api_info_id, api_info.id)
        self.assertEqual(relation.api_info_binding_status, "bound")
        self.assertIn("保留当前", relation.api_info_binding_reason)

    def test_snapshot_backfill_audits_then_links_historical_case(self):
        self.run_scan("8" * 40, [self.case_item("case-backfill", "历史关系回填")])
        case_snapshot = ModuleCoverageCaseSnapshot.objects.get()
        interface_snapshot_id = case_snapshot.interface_snapshot_id
        payload = dict(case_snapshot.payload)
        payload.pop("test_scenario")
        payload.pop("core_assertion")
        payload.pop("interface_source_key")
        case_snapshot.payload = payload
        case_snapshot.interface_snapshot = None
        case_snapshot.save(update_fields=["payload", "interface_snapshot"])
        interface_snapshot = ModuleCoverageInterfaceSnapshot.objects.get(id=interface_snapshot_id)
        interface_snapshot.mermaid = """flowchart TD
    request[请求] --> controller[Controller]
    controller --> boundary[未解析边界：Controller 后业务链路待逐接口补充]
"""
        interface_snapshot.node_ids = ["request", "controller", "boundary"]
        interface_snapshot.resolution_status = "resolved"
        interface_snapshot.resolution_reason = ""
        interface_snapshot.save(update_fields=[
            "mermaid", "node_ids", "resolution_status", "resolution_reason",
        ])
        coverage_case = ModuleCoverageCase.objects.get(source_key="case-backfill")
        coverage_case.coverage_validity = "valid"
        coverage_case.coverage_validity_reason = ""
        coverage_case.save(update_fields=["coverage_validity", "coverage_validity_reason"])

        placeholder_page = ModuleCoverageService.interface_page(
            ModuleCoverageInterfaceSnapshot.objects.select_related("scan").all(),
            resolution_status="placeholder",
        )
        resolved_page = ModuleCoverageService.interface_page(
            ModuleCoverageInterfaceSnapshot.objects.select_related("scan").all(),
            resolution_status="resolved",
        )
        self.assertEqual(placeholder_page["count"], 1)
        self.assertEqual(placeholder_page["items"][0]["resolution_status"], "placeholder")
        self.assertEqual(resolved_page["count"], 0)

        call_command("backfill_module_coverage_snapshot_links", stdout=StringIO())
        case_snapshot.refresh_from_db()
        self.assertIsNone(case_snapshot.interface_snapshot_id)

        call_command(
            "backfill_module_coverage_snapshot_links",
            "--execute",
            stdout=StringIO(),
        )
        case_snapshot.refresh_from_db()
        interface_snapshot.refresh_from_db()
        coverage_case.refresh_from_db()
        self.assertEqual(case_snapshot.interface_snapshot_id, interface_snapshot_id)
        self.assertEqual(interface_snapshot.resolution_status, "placeholder")
        self.assertEqual(coverage_case.coverage_validity, "invalid")
        self.assertIn("Schema v3", coverage_case.coverage_validity_reason)
        metrics = ModuleCoverageService.metrics(self.product.id, self.module.id)
        self.assertEqual(metrics["effective_completed_case_count"], 0)
        self.assertEqual(metrics["interface_resolution_rate"], 0)
