import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.auto_api.api.views.module_coverage_case import ModuleCoverageCaseViews
from src.apps.auto_api.services.module_coverage import ModuleCoverageService
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService


def queryset(rows=()):
    result = MagicMock()
    result.__iter__.side_effect = lambda: iter(rows)
    result.filter.return_value = result
    result.select_related.return_value = result
    result.order_by.return_value = result
    return result


def module(identity, parent=None, product=1):
    return SimpleNamespace(
        id=identity, parent_id=parent.id if parent else None, project_product_id=product,
        project_product=SimpleNamespace(name="后端服务", project=SimpleNamespace(name="测试项目")),
        name=f"模块{identity}", get_full_path=lambda: f"{parent.get_full_path()}/模块{identity}" if parent else f"模块{identity}",
    )


def scan(identity, module_id, **kwargs):
    return SimpleNamespace(id=identity, module_id=module_id, project_product_id=1,
                           **{"include_descendants": False, "status": "completed", "scan_mode": "full",
                              "scope_type": "module", "summary": {}, **kwargs})


def interface(identity, module_id, **kwargs):
    return SimpleNamespace(id=identity, module_id=module_id, project_product_id=1, repository_key="backend",
                           branch="main", source_key_hash=f"source-{identity}", interface_name="查询订单",
                           method="GET", url="/api/contracts",
                           **{"mermaid": "flowchart TD\nrequest --> result", "node_ids": ["request", "result"],
                              "api_info_id": None, "api_info_binding_status": "unbound", **kwargs})


def case(identity, interface_id, module_id, **kwargs):
    return SimpleNamespace(id=identity, module_id=module_id, project_product_id=1,
                           repository_key="backend", branch="main", interface_source_key_hash=f"source-{interface_id}",
                           **{"status": "completed", "api_case_id": 100, "coverage_validity": "valid", **kwargs})


class ModuleCoverageOverviewTests(SimpleTestCase):
    def test_interface_coverage_partitions_all_discovered_interfaces(self):
        result = self.overview([module(1)], interfaces=[interface(i, 1) for i in range(1, 6)], cases=[
            case(1, 1, 1), case(2, 1, 1, status="deferred"),
            case(3, 2, 1), case(4, 2, 1, status="pending_create", api_case_id=None),
            case(5, 3, 1, status="deferred"),
            case(6, 4, 1, coverage_validity="invalid"),
        ])
        summary = result["summary"]
        self.assertEqual(summary["covered_interface_count"], 1)
        self.assertEqual(summary["partial_interface_count"], 1)
        self.assertEqual(summary["uncovered_interface_count"], 2)
        self.assertEqual(summary["deferred_interface_count"], 1)
        self.assertEqual(summary["interface_coverage_rate"], 20)
        self.assertEqual(sum(summary[key] for key in (
            "covered_interface_count", "partial_interface_count",
            "uncovered_interface_count", "deferred_interface_count",
        )), summary["interface_count"])

    def test_inventory_interfaces_without_scenes_are_uncovered(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1, mermaid="", node_ids=[])])
        self.assertEqual(result["summary"]["uncovered_interface_count"], 1)
        self.assertEqual(result["summary"]["interface_coverage_rate"], 0)

    def test_unresolved_chain_does_not_count_as_covered_interface(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1, mermaid="", node_ids=[])],
                               cases=[case(1, 1, 1)])
        self.assertEqual(result["summary"]["covered_interface_count"], 0)
        self.assertEqual(result["summary"]["uncovered_interface_count"], 1)

    def test_project_scan_progress_is_independent_of_module_selection(self):
        modules = [module(1), module(2), module(3)]
        full = self.overview(modules, scans=[scan(1, 1)])
        filtered = self.overview(modules, scans=[scan(1, 1)], module_ids=[2])
        self.assertEqual(filtered["project_scan_summary"], full["project_scan_summary"])
        self.assertEqual(filtered["project_scan_summary"], {"leaf_count": 3, "scanned_count": 1, "unscanned_count": 2})
        self.assertEqual(filtered["summary"]["leaf_count"], 1)
        self.assertEqual([row["id"] for row in filtered["modules"]], [2])

    def overview(self, modules, interfaces=(), cases=(), scans=(), **kwargs):
        with patch.object(ModuleCoverageService, "case_coverage_assessment", return_value={"status": "valid"}):
            return ModuleCoverageService.overview(modules=queryset(modules), interfaces=queryset(interfaces),
                                                  cases=queryset(cases), scans=queryset(scans), **kwargs)

    def test_unscanned_modules_and_unknown_denominators_are_retained(self):
        result = self.overview([module(1), module(2)])
        self.assertEqual(result["summary"]["unscanned_count"], 2)
        self.assertIsNone(result["summary"]["binding_rate"])
        self.assertIsNone(result["summary"]["automation_rate"])
        self.assertIsNone(result["summary"]["interface_coverage_rate"])
        self.assertEqual(len(result["modules"]), 2)

    def test_ancestor_full_scan_applies_only_when_descendants_included(self):
        root = module(1)
        child = module(2, root)
        for include, expected in ((False, False), (True, True)):
            with self.subTest(include=include):
                result = self.overview([root, child], scans=[scan(1, 1, include_descendants=include)])
                self.assertEqual(result["modules"][1]["scan_completed"], expected)

    def test_partial_incremental_or_unapplied_scans_do_not_prove_full_coverage(self):
        for change in ({"status": "uploading"}, {"status": "completed_with_gaps"},
                       {"status": "cancelled"}, {"scan_mode": "incremental"}, {"scope_type": "interface"},
                       {"summary": {"inventory_only": True}}):
            with self.subTest(change=change):
                result = self.overview([module(1)], scans=[scan(1, 1, **change)])
                self.assertFalse(result["modules"][0]["scan_completed"])
                self.assertEqual(result["modules"][0]["latest_scan_id"], 1)

    def test_latest_failed_audit_does_not_hide_previous_applied_baseline(self):
        result = self.overview([module(1)], scans=[scan(2, 1, status="completed_with_gaps"), scan(1, 1)])
        self.assertEqual(result["modules"][0]["applied_scan_id"], 1)
        self.assertEqual(result["modules"][0]["latest_scan_id"], 2)

    def test_parent_rollup_does_not_duplicate_summary_counts(self):
        root = module(1)
        child = module(2, root)
        result = self.overview([root, child], interfaces=[interface(1, 2, api_info_id=9, api_info_binding_status="bound")],
                               cases=[case(1, 1, 2), case(2, 1, 2, status="pending_create", api_case_id=None)])
        self.assertEqual([row["interface_count"] for row in result["modules"]], [1, 1])
        self.assertEqual(result["summary"]["interface_count"], 1)
        self.assertEqual(result["summary"]["binding_rate"], 100)
        self.assertEqual(result["summary"]["automation_rate"], 50)
        self.assertEqual(result["summary"]["partial_interface_count"], 1)
        self.assertEqual([row["partial_interface_count"] for row in result["modules"]], [1, 1])

    def test_bound_id_does_not_override_binding_conflict(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1, api_info_id=9, api_info_binding_status="mismatch")])
        self.assertEqual(result["summary"]["bound_count"], 0)
        self.assertFalse(result["interface_gaps"][0]["bound"])

    def test_deferred_unbound_and_invalid_cases_are_not_completed(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1)], cases=[
            case(1, 1, 1, status="deferred"), case(2, 1, 1, api_case_id=None),
            case(3, 1, 1, coverage_validity="pending_review"), case(4, 1, 1, coverage_validity="invalid"),
        ])
        self.assertEqual(result["summary"]["completed_count"], 0)
        self.assertEqual(result["summary"]["target_count"], 3)
        self.assertEqual(result["summary"]["deferred_count"], 1)
        self.assertEqual(result["summary"]["incomplete_interface_count"], 1)

    def test_deferred_only_unbound_interface_is_only_a_binding_gap(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1)], cases=[case(1, 1, 1, status="deferred")])
        self.assertIsNone(result["summary"]["automation_rate"])
        self.assertEqual(result["interface_gap_count"], 1)
        self.assertEqual(result["summary"]["incomplete_interface_count"], 0)
        self.assertFalse(result["interface_gaps"][0]["incomplete"])

    def test_deferred_cases_do_not_make_bound_interfaces_incomplete(self):
        for cases, expected_rate in (([case(1, 1, 1, status="deferred")], None),
                                     ([case(1, 1, 1), case(2, 1, 1, status="deferred")], 100)):
            with self.subTest(expected_rate=expected_rate):
                result = self.overview([module(1)], interfaces=[
                    interface(1, 1, api_info_id=9, api_info_binding_status="bound"),
                ], cases=cases)
                self.assertEqual(result["summary"]["automation_rate"], expected_rate)
                self.assertEqual(result["summary"]["deferred_count"], 1)
                self.assertEqual(result["summary"]["incomplete_interface_count"], 0)
                self.assertEqual(result["interface_gap_count"], 0)

    def test_missing_or_pending_scenes_still_make_bound_interfaces_incomplete(self):
        for cases in ([], [case(1, 1, 1, status="pending_create", api_case_id=None),
                           case(2, 1, 1, status="deferred")]):
            with self.subTest(cases=cases):
                result = self.overview([module(1)], interfaces=[
                    interface(1, 1, api_info_id=9, api_info_binding_status="bound"),
                ], cases=cases)
                self.assertEqual(result["summary"]["incomplete_interface_count"], 1)
                self.assertEqual(result["interface_gap_count"], 1)

    def test_interface_page_coverage_status_excludes_deferred_from_targets(self):
        target = MagicMock()
        for key, value in vars(interface(1, 1)).items():
            setattr(target, key, value)
        target.module_interface_id = None
        source = queryset([target])
        source.count.return_value = 1
        source.__getitem__.return_value = [target]
        for total, completed, deferred, expected in ((1, 1, 2, "covered"),
                                                     (0, 0, 2, "deferred"),
                                                     (2, 1, 2, "partial"),
                                                     (0, 0, 0, "uncovered")):
            with self.subTest(expected=expected):
                stats = {"project_product_id": 1, "module_id": 1, "repository_key": "backend",
                         "branch": "main", "interface_source_key_hash": "source-1",
                         "target_case_count": total, "effective_completed_case_count": completed,
                         "deferred_case_count": deferred}
                cases = MagicMock()
                cases.filter.return_value.values.return_value.annotate.return_value = [stats]
                with patch.object(ModuleCoverageService, "active_cases", return_value=cases), \
                        patch("src.apps.auto_api.services.module_coverage_parts.query."
                              "ModuleCoverageInterfaceSnapshot.objects") as snapshots:
                    snapshots.filter.return_value.values.return_value.annotate.return_value = []
                    result = ModuleCoverageService.interface_page(source)
                self.assertEqual(result["items"][0]["coverage_status"], expected)

    def test_actual_case_assessment_rejects_legacy_or_incompatible_snapshot(self):
        from src.apps.auto_api.tests.test_module_coverage import valid_payload

        target = interface(1, 1)
        target.module_interface_id = None
        target.is_current = True
        target.lifecycle_status = "active"
        target.removed_at = None
        target.branch_ids = ["authorized", "denied"]
        target.node_ids = ["request", "auth", "result", "denied"]
        target.source_key_hash = hashlib.sha256(b"post:/api/contracts/search").hexdigest()
        item = case(1, 1, 1)
        item.interface_source_key_hash = target.source_key_hash
        item.module_interface_id = None
        for payload, expected in ((valid_payload(), 1), ({"test_scenario": "旧格式"}, 0)):
            with self.subTest(payload=payload):
                item.current_snapshot = SimpleNamespace(payload=payload, interface_snapshot=None)
                result = ModuleCoverageService.overview(modules=queryset([module(1)]), interfaces=queryset([target]),
                                                        cases=queryset([item]), scans=queryset())
                self.assertEqual(result["summary"]["completed_count"], expected)

    def test_selected_module_and_scoped_module_catalog_do_not_leak_other_products(self):
        result = self.overview([module(1), module(2)], interfaces=[interface(1, 1), interface(2, 2), interface(3, 99)], module_ids=[2])
        self.assertEqual([row["id"] for row in result["modules"]], [2])
        self.assertEqual(result["summary"]["interface_count"], 1)
        self.assertEqual(result["summary"]["uncovered_interface_count"], 1)
        self.assertEqual([row["module_id"] for row in result["interface_gaps"]], [2])

    def test_gap_list_is_bounded_but_count_remains_complete(self):
        result = self.overview([module(1)], interfaces=[interface(i, 1) for i in range(25)])
        self.assertEqual(len(result["interface_gaps"]), 20)
        self.assertEqual(result["interface_gap_count"], 25)

    def test_repository_and_branch_apply_to_all_asset_queries(self):
        inputs = {name: queryset() for name in ("modules", "interfaces", "cases", "scans")}
        ModuleCoverageService.overview(**inputs, repository_key="backend", branch="main")
        for name in ("interfaces", "cases", "scans"):
            inputs[name].filter.assert_any_call(repository_key="backend")
            inputs[name].filter.assert_any_call(branch="main")

    def test_overview_route_requires_page_permission(self):
        resolved = resolve("/api/api/module-coverage/overview")
        self.assertEqual(resolved.func.actions["get"], "overview")
        view = ModuleCoverageCaseViews()
        view.action = "overview"
        user = SimpleNamespace(id=1)
        request = SimpleNamespace(method="GET", path="/api/module-coverage/overview", data={},
                                  query_params=QueryDict(), user=SimpleNamespace(user_obj=user))
        with patch.object(PermissionMenuService, "is_effective_super_admin", return_value=False):
            for keys, expected in (({"api.module_coverage"}, True), ({"index.home"}, False), (set(), False)):
                with patch.object(PermissionMenuService, "permission_keys_for_user", return_value=keys):
                    self.assertEqual(MenuActionPermission().has_permission(request, view), expected)

    def test_all_overview_sources_are_project_scoped(self):
        request = SimpleNamespace(query_params=QueryDict("project_product=1"))
        with patch("src.apps.auto_api.api.views.module_coverage_case.require_project_scope") as require_scope, \
                patch("src.apps.auto_api.api.views.module_coverage_case.scope_queryset", side_effect=lambda req, qs: qs) as scope, \
                patch.object(ModuleCoverageService, "overview", return_value={}) as overview:
            ModuleCoverageCaseViews().overview(request)
        require_scope.assert_called_once_with(request, 1)
        self.assertEqual(scope.call_count, 4)
        self.assertIn("modules", overview.call_args.kwargs)
