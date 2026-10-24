from .module_coverage_parts.completion import ModuleCoverageCompletionMixin
from .module_coverage_parts.execution import ModuleCoverageExecutionMixin
from .module_coverage_parts.foundation import ModuleCoverageFoundationMixin
from .module_coverage_parts.query import ModuleCoverageQueryMixin
from .module_coverage_parts.scan import ModuleCoverageScanMixin
from .module_coverage_parts.overview import ModuleCoverageOverviewMixin


class ModuleCoverageService(ModuleCoverageFoundationMixin, ModuleCoverageScanMixin, ModuleCoverageCompletionMixin,
                            ModuleCoverageQueryMixin, ModuleCoverageExecutionMixin, ModuleCoverageOverviewMixin):
    MAX_BATCH_SIZE = 100
    PLACEHOLDER_FLOW_MARKERS = (
        "Controller 后业务链路待逐接口补充",
        "业务链路待逐接口补充",
    )
    UNRESOLVED_FLOW_MARKERS = ("未解析边界", "内部边界待解析")
    REQUIRED_SCAN_FIELDS = (
        "project_product_id", "repository_key", "branch",
        "commit_sha", "idempotency_key", "expected_case_count", "expected_interface_count",
    )
    REQUIRED_CURRENT_CASE_PAYLOAD_KEYS = (
        "test_scenario",
        "core_assertion",
        "test_ownership",
        "scenario_layer",
        "scenario_type",
        "scenario_tags",
        "covered_node_ids",
        "covered_branch_ids",
    )
