from src.apps.auto_api.services.coverage.parts.completion import ModuleCoverageCompletionMixin
from src.apps.auto_api.services.coverage.parts.execution import ModuleCoverageExecutionMixin
from src.apps.auto_api.services.coverage.parts.foundation import ModuleCoverageFoundationMixin
from src.apps.auto_api.services.coverage.parts.query import ModuleCoverageQueryMixin
from src.apps.auto_api.services.coverage.parts.scan import ModuleCoverageScanMixin
from src.apps.auto_api.services.coverage.parts.overview import ModuleCoverageOverviewMixin
from src.apps.auto_api.services.coverage.parts.policy import ModuleCoveragePolicyMixin


class ModuleCoverageService(ModuleCoveragePolicyMixin, ModuleCoverageFoundationMixin, ModuleCoverageScanMixin, ModuleCoverageCompletionMixin,
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
