import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.auto_api.api.views.module_coverage_case import ModuleCoverageCaseViews
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService


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
                              "scope_type": "module", "summary": {}, "repository_key": "backend",
                              "branch": "main", "commit_sha": "a" * 40, **kwargs})


def interface(identity, module_id, **kwargs):
    return SimpleNamespace(id=identity, module_id=module_id, project_product_id=1, repository_key="backend",
                           branch="main", source_key_hash=f"source-{identity}", interface_name="查询订单",
                           method="GET", url="/api/contracts",
                           **{"mermaid": "flowchart TD\nrequest --> result", "node_ids": ["request", "result"],
                              "api_info_id": None, "api_info_binding_status": "unbound",
                              "scan": scan(1, module_id), "gap_reason": "", "module_interface": None, **kwargs})


def case(identity, interface_id, module_id, **kwargs):
    return SimpleNamespace(id=identity, module_id=module_id, project_product_id=1,
                           repository_key="backend", branch="main", interface_source_key_hash=f"source-{interface_id}",
                           **{"status": "completed", "api_case_id": 100, "coverage_validity": "valid",
                              "api_case_revision_id": None, "api_case_revision": None,
                              "api_case": SimpleNamespace(id=100, project_product_id=1, module_id=module_id),
                              "current_snapshot": SimpleNamespace(scan=scan(1, module_id), payload={
                                  key: [] for key in ModuleCoverageService.REQUIRED_CURRENT_CASE_PAYLOAD_KEYS}), **kwargs})


class ModuleCoverageOverviewTests(SimpleTestCase):
    def test_analysis_gap_keeps_bindings_and_scene_progress_but_not_full_coverage(self):
        for options in (
            {"gap_reason": "缺少业务分支"},
            {"scan": scan(1, 1, summary={"inventory_only": True})},
            {"module_interface": SimpleNamespace(coverage_policy="included", last_seen_scan=scan(2, 1, commit_sha="b" * 40))},
        ):
            with self.subTest(options=options):
                asset = case(1, 1, 1)
                result = self.overview([module(1)], interfaces=[interface(
                    1, 1, api_info_id=8, api_info_binding_status="bound", **options,
                )], cases=[asset])
                self.assertEqual(result["summary"]["covered_interface_count"], 0)
                self.assertEqual(result["summary"]["partial_interface_count"], 1)
                self.assertEqual(result["summary"]["completed_count"], 1)
                self.assertEqual(result["summary"]["bound_count"], 1)
                self.assertEqual(result["summary"]["incomplete_interface_count"], 1)
                self.assertEqual(result["interface_gap_count"], 1)
                self.assertEqual(asset.api_case_id, 100)

    def test_inventory_completes_stage_one_without_graphs_or_cases(self):
        result = self.overview([module(1)], interfaces=[interface(1, 1, mermaid="", node_ids=[],
                              scan=scan(10, 1, summary={"inventory_only": True}))],
                              scans=[scan(10, 1, summary={"inventory_only": True})])
        self.assertTrue(result["modules"][0]["inventory_completed"])
        self.assertFalse(result["modules"][0]["scan_completed"])
        self.assertEqual(result["project_inventory_summary"]["inventory_rate"], 100)
        self.assertEqual(result["summary"]["pending_analysis_count"], 1)
        self.assertEqual(result["summary"]["analysis_rate"], 0)

    def test_inventory_requires_all_known_repository_baselines(self):
        for extra in (scan(2, 1, repository_key="shared", scope_type="interface"),
                      scan(2, 1, repository_key="shared", status="uploading"),
                      scan(2, 1, commit_sha="b" * 40, scope_type="interface")):
            result = self.overview([module(1)], scans=[scan(1, 1), extra])
            self.assertFalse(result["modules"][0]["inventory_completed"])
        result = self.overview([module(1)], scans=[scan(1, 1), scan(2, 1, repository_key="shared")])
        self.assertEqual(result["modules"][0]["inventory_scan_ids"], [2, 1])
        self.assertTrue(result["modules"][0]["inventory_completed"])

    def test_empty_module_inventory_summary_follows_module_selection(self):
        modules = [module(1), module(2)]
        result = self.overview(modules, scans=[scan(1, 1, summary={"inventory_only": True})], module_ids=[2])
        self.assertEqual(result["project_inventory_summary"]["inventoried_count"], 0)
        self.assertEqual(result["summary"]["inventoried_count"], 0)
        selected = self.overview(modules, scans=[scan(1, 1, summary={"inventory_only": True})], module_ids=[1])
        self.assertEqual(selected["project_inventory_summary"]["inventoried_count"], 1)
        self.assertEqual(selected["project_inventory_summary"]["inventory_rate"], 100)

    def test_analysis_requires_current_graph_and_valid_scenarios_not_apiinfo_binding(self):
        result = self.overview([module(1)], interfaces=[interface(i, 1) for i in (1, 2)],
                               cases=[case(1, 1, 1, status="pending_create", api_case_id=None)])
        self.assertEqual(result["summary"]["analyzed_interface_count"], 1)
        self.assertEqual(result["summary"]["pending_analysis_count"], 1)
        self.assertEqual(result["summary"]["bound_count"], 0)
        self.assertEqual(result["summary"]["analysis_rate"], 50)

    def test_analysis_partitions_gap_and_policy_without_expanding_exclusions(self):
        result = self.overview([module(1)], interfaces=[
            interface(1, 1, gap_reason="缺少业务处理器"),
            interface(2, 1, module_interface=SimpleNamespace(coverage_policy="deferred")),
            interface(3, 1, module_interface=SimpleNamespace(coverage_policy="excluded")),
        ])
        self.assertEqual(result["summary"]["analysis_gap_count"], 1)
        self.assertEqual(result["summary"]["deferred_analysis_count"], 1)
        self.assertEqual(result["summary"]["excluded_interface_count"], 1)
        self.assertEqual(result["summary"]["interface_count"], 2)

    def test_new_inventory_revision_does_not_revalidate_old_analysis(self):
        relation = SimpleNamespace(coverage_policy="included", last_seen_scan=scan(2, 1, commit_sha="b" * 40))
        target = interface(1, 1, module_interface=relation)
        result = self.overview([module(1)], interfaces=[target], cases=[case(1, 1, 1)])
        self.assertEqual(result["summary"]["analysis_review_count"], 1)
        self.assertEqual(result["summary"]["analysis_gap_count"], 0)
        self.assertEqual(result["summary"]["analyzed_interface_count"], 0)

    def test_analysis_six_states_explain_reason_and_recover_without_changing_bindings(self):
        relation = SimpleNamespace(coverage_policy="included", last_seen_scan=scan(2, 1, commit_sha="b" * 40))
        target = interface(1, 1, module_interface=relation, api_info_id=8)
        assess = lambda: ModuleCoverageService.interface_analysis_assessment(target, 1, 1)
        result = assess()
        self.assertEqual(result["analysis_status"], "review")
        self.assertIn("a" * 40, result["analysis_reason"])
        self.assertEqual(result["latest_inventory_commit_sha"], "b" * 40)
        self.assertEqual(target.api_info_id, 8)
        target.scan = relation.last_seen_scan
        self.assertEqual(assess()["analysis_status"], "completed")
        target.gap_reason = "缺少异常分支"
        self.assertEqual(assess()["analysis_reason"], "缺少异常分支")
        self.assertEqual(assess()["analysis_status"], "gap")
        relation.coverage_policy = "deferred"
        self.assertEqual(assess()["analysis_status"], "deferred")
        relation.coverage_policy = "excluded"
        self.assertEqual(assess()["analysis_status"], "excluded")
        relation.coverage_policy = "included"
        target.mermaid = ""
        self.assertEqual(assess()["analysis_status"], "pending")

    def test_analysis_filters_use_overview_assessment_before_pagination(self):
        targets = []
        for identity in range(1, 6):
            target = MagicMock()
            for key, value in vars(interface(identity, 1)).items():
                setattr(target, key, value)
            target.module_interface_id = None
            targets.append(target)
        targets[0].mermaid = ""
        targets[2].gap_reason = "缺少业务来源"
        targets[3].module_interface = SimpleNamespace(coverage_policy="deferred")
        cases = queryset([case(2, 2, 1), case(5, 5, 1)])
        cases.values.return_value.annotate.return_value = []
        with patch.object(ModuleCoverageService, "active_cases", return_value=cases), \
                patch.object(ModuleCoverageService, "case_coverage_assessment", return_value={"status": "valid"}), \
                patch("src.apps.auto_api.services.coverage.parts.query.ModuleCoverageInterfaceSnapshot.objects") as snapshots:
            snapshots.filter.return_value.values.return_value.annotate.return_value = []
            result = ModuleCoverageService.interface_page(queryset(targets), page=2, page_size=1,
                                                          analysis_statuses=["completed"])
            self.assertEqual(result["count"], 2)
            self.assertEqual([row["id"] for row in result["items"]], [5])
            result = ModuleCoverageService.interface_page(queryset(targets), analysis_statuses=["pending", "gap"])
            self.assertEqual([row["id"] for row in result["items"]], [1, 3])

    def test_invalid_scene_keeps_analysis_in_gap(self):
        with patch.object(ModuleCoverageService, "case_coverage_assessment",
                          side_effect=[{"status": "valid"}, {"status": "invalid"},
                                       {"status": "valid"}, {"status": "invalid"}]):
            result = ModuleCoverageService.overview(modules=queryset([module(1)]), interfaces=queryset([interface(1, 1)]),
                                                    cases=queryset([case(1, 1, 1), case(2, 1, 1)]), scans=queryset())
        self.assertEqual(result["summary"]["analysis_gap_count"], 1)


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

    def test_scan_and_inventory_progress_follow_module_selection(self):
        modules = [module(1), module(2), module(3)]
        full = self.overview(modules, scans=[scan(1, 1)])
        filtered = self.overview(modules, scans=[scan(1, 1)], module_ids=[2])
        self.assertEqual(full["project_scan_summary"], {"leaf_count": 3, "scanned_count": 1, "unscanned_count": 2})
        self.assertEqual(filtered["project_scan_summary"], {"leaf_count": 1, "scanned_count": 0, "unscanned_count": 1})
        self.assertEqual(filtered["project_inventory_summary"]["leaf_count"], 1)
        self.assertEqual(filtered["project_inventory_summary"]["inventoried_count"], 0)
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
                cases.filter.return_value.select_related.return_value = [case(1, 1, 1)]
                with patch.object(ModuleCoverageService, "active_cases", return_value=cases), \
                        patch.object(ModuleCoverageService, "case_coverage_assessment", return_value={"status": "valid"}), \
                        patch("src.apps.auto_api.services.coverage.parts.query."
                              "ModuleCoverageInterfaceSnapshot.objects") as snapshots:
                    snapshots.filter.return_value.values.return_value.annotate.return_value = []
                    result = ModuleCoverageService.interface_page(source)
                self.assertEqual(result["items"][0]["coverage_status"], expected)

    def test_interface_progress_multi_filter_applies_before_pagination(self):
        targets = []
        for identity in range(1, 5):
            target = MagicMock()
            for key, value in vars(interface(identity, 1)).items():
                setattr(target, key, value)
            target.module_interface_id = None
            targets.append(target)
        targets[2].mermaid = ""
        targets[2].node_ids = []
        source = queryset(targets)
        stats = [{"project_product_id": 1, "module_id": 1, "repository_key": "backend",
                  "branch": "main", "interface_source_key_hash": f"source-{identity}",
                  "target_case_count": 1, "effective_completed_case_count": 1}
                 for identity in (2, 4)]
        cases = MagicMock()
        cases.filter.return_value.values.return_value.annotate.return_value = stats
        cases.filter.return_value.select_related.return_value = [case(2, 2, 1), case(4, 4, 1)]
        with patch.object(ModuleCoverageService, "active_cases", return_value=cases), \
                patch.object(ModuleCoverageService, "case_coverage_assessment", return_value={"status": "valid"}), \
                patch("src.apps.auto_api.services.coverage.parts.query."
                      "ModuleCoverageInterfaceSnapshot.objects") as snapshots:
            snapshots.filter.return_value.values.return_value.annotate.return_value = []
            result = ModuleCoverageService.interface_page(source, page=2, page_size=1,
                                                          coverage_statuses=["covered"])
            self.assertEqual(result["count"], 2)
            self.assertEqual([row["id"] for row in result["items"]], [4])
            result = ModuleCoverageService.interface_page(source, coverage_statuses=["covered", "uncovered"])
            self.assertEqual(result["count"], 4)
            result = ModuleCoverageService.interface_page(source, coverage_statuses=["partial"])
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["items"], [])
            result = ModuleCoverageService.interface_page(source, coverage_statuses=["uncovered"],
                                                          resolution_statuses=["resolved"])
            self.assertEqual(result["count"], 1)
            self.assertEqual([row["id"] for row in result["items"]], [1])

            targets[1].gap_reason = "当前分析缺少分支"
            result = ModuleCoverageService.interface_page(source, coverage_statuses=["covered"])
            self.assertEqual([row["id"] for row in result["items"]], [4])
            result = ModuleCoverageService.interface_page(source, coverage_statuses=["partial"], analysis_statuses=["gap"])
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["items"][0]["id"], 2)
            self.assertEqual(result["items"][0]["effective_completed_case_count"], 1)

    def test_interface_search_filters_database_fields_and_validates_states(self):
        from src.apps.auto_api.exceptions import AutoApiError
        source = queryset()
        source.count.return_value = 0
        source.__getitem__.return_value = []
        cases = MagicMock()
        cases.filter.return_value.values.return_value.annotate.return_value = []
        with patch.object(ModuleCoverageService, "active_cases", return_value=cases), \
                patch("src.apps.auto_api.services.coverage.parts.query."
                      "ModuleCoverageInterfaceSnapshot.objects") as snapshots:
            snapshots.filter.return_value.values.return_value.annotate.return_value = []
            ModuleCoverageService.interface_page(source, methods=["GET", "POST"],
                                                 sync_actions=["created", "updated"],
                                                 coverage_reason="外部服务", api_info_id=123)
            for condition in ({"method__in": ["GET", "POST"]}, {"sync_action__in": ["created", "updated"]},
                              {"module_interface__coverage_reason__icontains": "外部服务"}, {"api_info_id": 123}):
                source.filter.assert_any_call(**condition)
            for condition in ({"coverage_statuses": ["bad"]}, {"resolution_statuses": ["bad"]},
                              {"sync_actions": ["bad"]}):
                with self.assertRaises(AutoApiError):
                    ModuleCoverageService.interface_page(source, **condition)

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
        target.method = valid_payload()["method"]
        target.url = valid_payload()["url"]
        target.interface_name = valid_payload()["interface_name"]
        item = case(1, 1, 1)
        item.interface_source_key_hash = target.source_key_hash
        item.module_interface_id = None
        for payload, expected in ((valid_payload(), 1), ({"test_scenario": "旧格式"}, 0)):
            with self.subTest(payload=payload):
                item.current_snapshot = SimpleNamespace(payload=payload, interface_snapshot=None, scan=scan(1, 1))
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
        request = SimpleNamespace(method="GET", path="/api/api/module-coverage/overview", data={},
                                  query_params=QueryDict(), user=SimpleNamespace(user_obj=user))
        with patch.object(PermissionMenuService, "is_effective_super_admin", return_value=False):
            for keys, expected in (({"api.module_coverage:read"}, True), ({"index.home:read"}, False), (set(), False)):
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
