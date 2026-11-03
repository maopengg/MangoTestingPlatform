import re
from typing import Annotated, Literal

from pydantic import Field, StrictInt, field_validator, model_validator

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.auto_api.enums.module_coverage import ModuleCoverageTestOwnership, ModuleCoveragePolicy
from src.common.schemas import StrictSchema


class ModuleCoveragePolicyUpdate(StrictSchema):
    interface_ids: list[Annotated[StrictInt, Field(gt=0)]] = Field(min_length=1, max_length=100)
    policy: ModuleCoveragePolicy
    reason: str = Field(default="", max_length=2000)


class ModuleCoverageCodeEvidence(StrictSchema):
    path: str = Field(min_length=1, max_length=1024)
    symbol: str | None = Field(default=None, max_length=512)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_lines(self):
        if self.start_line and self.end_line and self.end_line < self.start_line:
            raise ValueError("代码证据结束行不能小于开始行")
        return self


class ModuleCoverageBaselineCommit(StrictSchema):
    repository: str = Field(min_length=1, max_length=256)
    commit_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")


def validate_mermaid_flow(value: str) -> str:
    source = value.strip()
    meaningful_lines = [
        line.strip() for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("%%")
    ]
    if not meaningful_lines or not re.match(
            r"^(flowchart|graph)\s+(TB|TD|BT|RL|LR)\b",
            meaningful_lines[0],
    ):
        raise ValueError("调用流程必须是 Mermaid flowchart/graph 文本")
    lowered = source.lower()
    if "%%{" in source or re.search(r"(?m)^\s*click\s+", lowered):
        raise ValueError("调用流程不允许 Mermaid 初始化指令或 click 交互")
    return source


def unique_identifiers(value: list[str]) -> list[str]:
    values = [item.strip() for item in value]
    if len(values) != len(set(values)) or any(
            not re.fullmatch(r"[A-Za-z_][\w-]*", item) for item in values
    ):
        raise ValueError("节点或分支 ID 必须非空、唯一且格式稳定")
    return values


MERMAID_EDGE_PATTERN = re.compile(r"(-->|-\.->|==>)")
MERMAID_NODE_PATTERN = re.compile(r"^\s*([A-Za-z_][\w-]*)")
MERMAID_EDGE_ID_PATTERN = re.compile(r"([A-Za-z_][\w-]*)@\s*$")


def validate_mermaid_structure(source: str, node_ids: list[str], branch_ids: list[str]) -> None:
    """Validate the deterministic flowchart subset emitted by the coverage Skill."""
    declared_nodes = set(node_ids)
    seen_nodes: set[str] = set()
    seen_branches: set[str] = set()
    edges: list[tuple[str, str]] = []
    root: str | None = None

    for raw_line in source.splitlines()[1:]:
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        edge_match = MERMAID_EDGE_PATTERN.search(line)
        if edge_match is None:
            node_match = MERMAID_NODE_PATTERN.match(line)
            if node_match and node_match.group(1) in declared_nodes:
                seen_nodes.add(node_match.group(1))
                root = root or node_match.group(1)
            continue

        left = line[:edge_match.start()].strip()
        right = line[edge_match.end():].strip()
        source_match = MERMAID_NODE_PATTERN.match(left)
        if source_match is None:
            raise ValueError("Mermaid 边缺少有效来源节点")
        source_node = source_match.group(1)
        edge_id_match = MERMAID_EDGE_ID_PATTERN.search(left)
        if edge_id_match:
            seen_branches.add(edge_id_match.group(1))
        if right.startswith("|"):
            label_end = right.find("|", 1)
            if label_end < 0:
                raise ValueError("Mermaid 分支标签未闭合")
            right = right[label_end + 1:].strip()
        target_match = MERMAID_NODE_PATTERN.match(right)
        if target_match is None:
            raise ValueError("Mermaid 边缺少有效目标节点")
        target_node = target_match.group(1)
        root = root or source_node
        seen_nodes.update((source_node, target_node))
        edges.append((source_node, target_node))

    missing_nodes = sorted(declared_nodes - seen_nodes)
    undeclared_nodes = sorted(seen_nodes - declared_nodes)
    missing_branches = sorted(set(branch_ids) - seen_branches)
    undeclared_branches = sorted(seen_branches - set(branch_ids))
    if missing_nodes:
        raise ValueError(f"节点清单包含未出现在 Mermaid 中的节点：{', '.join(missing_nodes)}")
    if undeclared_nodes:
        raise ValueError(f"Mermaid 包含未登记节点：{', '.join(undeclared_nodes)}")
    if missing_branches:
        raise ValueError(f"分支清单包含未绑定到 Mermaid 边的分支：{', '.join(missing_branches)}")
    if undeclared_branches:
        raise ValueError(f"Mermaid 包含未登记分支：{', '.join(undeclared_branches)}")
    if len(declared_nodes) > 1 and not edges:
        raise ValueError("多节点 Mermaid 必须包含连通边")
    if root:
        reachable = {root}
        changed = True
        while changed:
            changed = False
            for source_node, target_node in edges:
                if source_node in reachable and target_node not in reachable:
                    reachable.add(target_node)
                    changed = True
        unreachable = sorted(declared_nodes - reachable)
        if unreachable:
            raise ValueError(f"Mermaid 存在从入口不可达的节点：{', '.join(unreachable)}")


class ModuleCoverageInterfacePayload(StrictSchema):
    """一次接口扫描保存一张完整调用图，供多个 Case 复用。"""

    interface_name: str = Field(min_length=1, max_length=512)
    method: str = Field(min_length=1, max_length=16)
    url: str = Field(min_length=1, max_length=1024)
    mermaid: str = Field(default="", max_length=100_000)
    node_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    gap_reason: str | None = Field(default=None, max_length=4000)
    next_action: str | None = Field(default=None, max_length=4000)
    resumption_point: str | None = Field(default=None, max_length=4000)
    api_info_id: int | None = Field(default=None, ge=1)
    api_info_revision_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_api_info_revision(self):
        if self.api_info_revision_id and not self.api_info_id:
            raise ValueError("api_info_revision_id 必须与 api_info_id 一起提交")
        if not self.mermaid:
            if self.node_ids or self.branch_ids or any((self.gap_reason, self.next_action, self.resumption_point)):
                raise ValueError("纯接口清单不能包含无流程图的节点、分支或 Gap 信息")
            return self
        if not self.node_ids:
            raise ValueError("流程图必须同时提供节点清单")
        validate_mermaid_structure(self.mermaid, self.node_ids, self.branch_ids)
        has_internal_gap = any(
            marker in self.mermaid for marker in ("未解析边界", "内部边界待解析")
        ) and not any(
            marker in self.mermaid
            for marker in ("Controller 后业务链路待逐接口补充", "业务链路待逐接口补充")
        )
        gap_values = [self.gap_reason, self.next_action, self.resumption_point]
        if has_internal_gap and not all(value and value.strip() for value in gap_values):
            raise ValueError("内部未解析边界必须填写 gap_reason、next_action 和 resumption_point")
        if not has_internal_gap and any(value and value.strip() for value in gap_values):
            raise ValueError("仅存在内部未解析边界时才能提交 Gap 处理信息")
        return self

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str):
        return value.strip().upper()

    @field_validator("gap_reason", "next_action", "resumption_point")
    @classmethod
    def normalize_gap_text(cls, value: str | None):
        return value.strip() if value and value.strip() else None

    @field_validator("mermaid")
    @classmethod
    def validate_mermaid(cls, value: str):
        return validate_mermaid_flow(value) if value.strip() else ""

    @field_validator("node_ids", "branch_ids")
    @classmethod
    def validate_identifiers(cls, value: list[str]):
        return unique_identifiers(value)


class ModuleCoverageCasePayload(StrictSchema):
    """Case 保存接口引用、独立测试场景与核心断言，以及接口全景图中的覆盖路径。"""

    interface_source_key: str = Field(min_length=1, max_length=512)
    secondary_module: str | None = Field(default=None, max_length=256)
    tertiary_module: str | None = Field(default=None, max_length=256)
    interface_name: str = Field(min_length=1, max_length=512)
    method: str = Field(min_length=1, max_length=16)
    url: str = Field(min_length=1, max_length=1024)
    case_title: str = Field(min_length=1, max_length=512)
    evidence_category: Literal[
                           "功能用例已核验", "设计已核验", "代码现状回归候选",
                       ] | None = None
    code_evidence: list[ModuleCoverageCodeEvidence] | str = Field(default_factory=list)
    baseline_commits: list[ModuleCoverageBaselineCommit] | str = Field(default_factory=list)
    test_scenario: str = Field(min_length=1)
    core_assertion: str = Field(min_length=1)
    preconditions: str | None = None
    data_strategy: str | None = None
    cleanup_strategy: str | None = None
    test_ownership: ModuleCoverageTestOwnership = ModuleCoverageTestOwnership.HTTP_API_AUTOMATION
    scenario_layer: Literal[0, 1, 2]
    scenario_type: Literal[0, 1, 2, 3, 4, 5]
    scenario_tags: list[str] = Field(
        min_length=1,
        description="执行场景，至少选择一个平台执行场景枚举值",
    )
    current_status: Literal["pending_create", "completed", "deferred"] = "pending_create"
    execution_result: Literal[
        "passed", "failed", "partial", "not_applicable", "not_executed",
    ] = "not_executed"
    remark: str | None = Field(
        default=None,
        description="备注；current_status=deferred 时必填，并在同一文本中明确暂不处理原因和重新启用条件",
    )
    covered_node_ids: list[str] = Field(min_length=1)
    covered_branch_ids: list[str] = Field(default_factory=list)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str):
        return value.strip().upper()

    @field_validator("remark")
    @classmethod
    def normalize_remark(cls, value: str | None):
        return value.strip() if value and value.strip() else None

    @field_validator("test_scenario", "core_assertion")
    @classmethod
    def normalize_scenario_text(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("测试场景和核心断言不能为空")
        return normalized

    @field_validator("scenario_tags")
    @classmethod
    def validate_scenario_tags(cls, value: list[str]):
        allowed = set(ApiCaseScenarioTagEnum.get_key_list())
        normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not normalized:
            raise ValueError("执行场景至少选择一项")
        invalid = [item for item in normalized if item not in allowed]
        if invalid:
            raise ValueError(f"执行场景包含无效值：{', '.join(invalid)}")
        return normalized

    @field_validator("covered_node_ids", "covered_branch_ids")
    @classmethod
    def validate_identifiers(cls, value: list[str]):
        return unique_identifiers(value)

    @model_validator(mode="after")
    def validate_status_contract(self):
        if self.current_status == "deferred" and not self.remark:
            raise ValueError(
                "current_status=deferred 时必须在 payload.remark 中同时填写暂不处理原因和重新启用条件"
            )
        allowed_results = {
            "pending_create": {"not_executed"},
            "completed": {"not_executed", "passed", "failed", "partial"},
            "deferred": {"not_applicable"},
        }
        if self.execution_result not in allowed_results[self.current_status]:
            raise ValueError(
                f"current_status={self.current_status} 与 execution_result={self.execution_result} 不一致",
            )
        if self.test_ownership == ModuleCoverageTestOwnership.UNIT_TEST and (
                self.current_status != "deferred" or self.execution_result != "not_applicable"
        ):
            raise ValueError("单元测试归属必须使用 deferred 和 not_applicable，且不能绑定 ApiCase")
        return self


class ModuleCoverageCaseUploadItem(StrictSchema):
    """MCP-visible Case upload envelope; binding fields belong outside the snapshot payload."""

    source_key: str = Field(min_length=1, max_length=512)
    payload: ModuleCoverageCasePayload
    module_id: int | None = Field(default=None, ge=1)
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    api_case_id: int | None = Field(default=None, ge=1)
    api_case_revision_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_binding_contract(self):
        if self.api_case_revision_id and not self.api_case_id:
            raise ValueError("api_case_revision_id 必须与 api_case_id 一起提交")
        if (self.payload.current_status == "completed") != bool(self.api_case_id):
            raise ValueError("current_status=completed 必须且只能在绑定 ApiCase 时提交")
        return self
