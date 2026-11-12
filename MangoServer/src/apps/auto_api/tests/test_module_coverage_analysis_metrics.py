from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService
from src.interfaces.mcp.tools.api.module_coverage import register_module_coverage_tools


BASE = "src.apps.auto_api.services.coverage.parts.overview"


class CoverageAnalysisMetricsTests(SimpleTestCase):
    def setUp(self):
        self.products = MagicMock()
        self.products.filter.return_value = self.products
        self.products.values_list.return_value = [10, 11]
        self.modules = MagicMock()
        self.modules.filter.return_value = self.modules
        self.modules.order_by.return_value = self.modules
        self.modules.select_related.return_value = self.modules
        self.modules.values_list.return_value = [(1, None), (2, 1), (3, 2), (4, None)]
        self.patches = [
            patch(BASE + ".TestCenterQuerySelector.project_product", return_value=self.products),
            patch(BASE + ".TestCenterQuerySelector.product_module", return_value=self.modules),
            patch(BASE + ".ApiQuerySelector.module_coverage_interface_snapshot"),
            patch(BASE + ".ApiQuerySelector.module_coverage_case"),
            patch(BASE + ".ApiQuerySelector.module_coverage_scan"),
            patch(BASE + ".PermissionMenuService.is_effective_super_admin", return_value=False),
            patch(BASE + ".ProjectProductScopeService.can_view_all_project_data", return_value=False),
            patch(BASE + ".ProjectProductScopeService.project_product_ids_for_user", return_value={10}),
            patch.object(ModuleCoverageService, "metrics", return_value={"case_total": 17}),
            patch.object(ModuleCoverageService, "overview", side_effect=self.overview),
        ]
        self.mocks = [item.start() for item in self.patches]
        for item in self.patches:
            self.addCleanup(item.stop)

    @staticmethod
    def overview(**kwargs):
        return {"summary": {"interface_count": 10, "bound_count": 7,
                            "target_count": 6, "completed_count": 4, "deferred_count": 3},
                "project_scan_summary": {"leaf_count": 4, "scanned_count": 1, "unscanned_count": 3},
                "project_inventory_summary": {"leaf_count": 4, "inventoried_count": 3, "uninventoried_count": 1, "inventory_rate": 75},
                "modules": [{"id": index} for index in range(25)]}

    def run_metrics(self, **kwargs):
        return ModuleCoverageService.analysis_metrics(user=SimpleNamespace(id=5), **kwargs)

    def test_project_and_product_are_intersected_after_authorization(self):
        result = self.run_metrics(project_id=8, project_product_id=10, repository_key="backend", branch="main")
        self.products.filter.assert_any_call(id__in={10})
        self.products.filter.assert_any_call(project_id=8)
        self.products.filter.assert_any_call(id=10)
        for source in self.mocks[2:5]:
            source.return_value.filter.assert_called_once_with(project_product_id__in=[10, 11])
        args = self.mocks[-1].call_args.kwargs
        self.assertEqual((args["repository_key"], args["branch"]), ("backend", "main"))
        self.assertEqual(result["overview"]["scope"]["project_id"], 8)

    def test_no_product_permission_never_means_all_products(self):
        self.mocks[7].return_value = set()
        self.products.values_list.return_value = []
        self.run_metrics(project_id=8)
        self.products.filter.assert_any_call(id__in=set())
        self.mocks[2].return_value.filter.assert_called_once_with(project_product_id__in=[])

    def test_admin_does_not_apply_empty_permission_set(self):
        self.mocks[5].return_value = True
        self.run_metrics(project_id=8)
        self.mocks[7].assert_not_called()
        self.products.filter.assert_called_once_with(project_id=8)

    def test_module_subtree_is_selected_without_losing_project_scan_scope(self):
        self.run_metrics(module_id=1)
        args = self.mocks[-1].call_args.kwargs
        self.assertEqual(args["module_ids"], {1, 2, 3})
        self.assertIs(args["modules"], self.modules)

    def test_missing_or_inaccessible_module_cannot_expand_to_all(self):
        self.run_metrics(module_id=999)
        self.assertEqual(self.mocks[-1].call_args.kwargs["module_ids"], [-1])

    def test_additive_summary_and_scan_rate_keep_legacy_fields(self):
        result = self.run_metrics()
        self.assertEqual(result["case_total"], 17)
        overview = result["overview"]
        self.assertEqual(overview["summary"]["unbound_count"], 3)
        self.assertEqual(overview["summary"]["incomplete_case_count"], 2)
        self.assertEqual(overview["summary"]["scenario_count"], 9)
        self.assertEqual(overview["project_scan_summary"]["scan_completion_rate"], 25)
        self.assertEqual(overview["project_inventory_summary"]["inventory_rate"], 75)
        self.assertIn("执行失败", overview["definitions"]["automation"])

    def test_zero_scan_denominator_is_unknown_not_completed(self):
        empty = self.overview()
        empty["project_scan_summary"] = {"leaf_count": 0, "scanned_count": 0, "unscanned_count": 0}
        self.mocks[-1].side_effect = None
        self.mocks[-1].return_value = empty
        self.assertIsNone(self.run_metrics()["overview"]["project_scan_summary"]["scan_completion_rate"])


class CoverageMetricsMcpTests(SimpleTestCase):
    def test_existing_tool_keeps_product_call_and_paginates_modules_only(self):
        class Capture:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func
                return register

        capture = Capture()
        register_module_coverage_tools(capture)
        self.assertNotIn("get_module_coverage_overview", capture.tools)
        with (
            patch("src.interfaces.mcp.tools.api.module_coverage.current_user", return_value="user"),
            patch.object(ModuleCoverageService, "analysis_metrics", side_effect=lambda **_: {
                "case_total": 17, "overview": CoverageAnalysisMetricsTests.overview(),
            }) as service,
        ):
            tool = capture.tools["get_module_coverage_metrics"]
            for guidance in ("只读统计", "binding_rate", "interface_coverage_rate", "automation_rate",
                             "不合成未经定义的总完成率", "须翻完各页", "账号可见数据"):
                self.assertIn(guidance, tool.__doc__)
            default = tool(10)
            self.assertEqual(default["data"]["overview"]["modules"]["count"], 25)
            self.assertEqual(len(default["data"]["overview"]["modules"]["items"]), 10)
            page = tool(project_id=8, page=2)["data"]
            self.assertEqual(page["overview"]["modules"]["items"][0]["id"], 10)
            self.assertEqual(page["overview"]["summary"]["interface_count"], 10)
            self.assertEqual(page["overview"]["project_inventory_summary"]["inventoried_count"], 3)
            self.assertEqual(service.call_args.kwargs["project_id"], 8)
            self.assertIsNone(service.call_args.kwargs["project_product_id"])
