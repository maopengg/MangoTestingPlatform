from typing import Any, Literal

from pydantic import Field

from src.common.schemas import StrictSchema


class AgentUiEvidencePolicy(StrictSchema):
    screenshot: Literal["none", "failure", "assertion", "each_step"] = "failure"
    upload_trace_on_failure: bool = False
    max_artifacts: int = Field(default=30, ge=1, le=100)


class AgentUiCapabilityManifest(StrictSchema):
    available_tools: list[str] = Field(default_factory=list, max_length=100)
    supports_screenshot: bool = False
    supports_file_upload: bool = False
    notes: str | None = Field(default=None, max_length=500)


class AgentUiAssertionResult(StrictSchema):
    name: str = Field(min_length=1, max_length=200)
    assertion_type: str = Field(min_length=1, max_length=80)
    status: Literal["passed", "failed", "blocked"]
    expected: str | None = Field(default=None, max_length=2000)
    actual: str | None = Field(default=None, max_length=2000)
    message: str | None = Field(default=None, max_length=2000)
    evidence_artifact_refs: list[str] = Field(default_factory=list, max_length=20)


class AgentUiToolCallSummary(StrictSchema):
    tool: str = Field(min_length=1, max_length=160)
    category: str = Field(default="browser", max_length=80)
    outcome: Literal["passed", "failed", "blocked"]
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)


class AgentUiStepReport(StrictSchema):
    idempotency_key: str = Field(min_length=8, max_length=128)
    status: Literal["passed", "failed", "blocked", "skipped"]
    summary: str = Field(min_length=1, max_length=2000)
    error_message: str | None = Field(default=None, max_length=4000)
    assertion_results: list[AgentUiAssertionResult] = Field(default_factory=list, max_length=100)
    observations: list[str] = Field(default_factory=list, max_length=100)
    artifact_refs: list[str] = Field(default_factory=list, max_length=30)
    tool_calls: list[AgentUiToolCallSummary] = Field(default_factory=list, max_length=200)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)


class AgentUiCompletionStep(StrictSchema):
    step_index: int = Field(ge=0)
    report: AgentUiStepReport


class AgentUiCompletionReport(StrictSchema):
    status: Literal["passed", "failed", "blocked"]
    summary: str = Field(min_length=1, max_length=2000)
    error_message: str | None = Field(default=None, max_length=4000)
    steps: list[AgentUiCompletionStep] = Field(default_factory=list, max_length=500)
    artifact_refs: list[str] = Field(default_factory=list, max_length=100)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)


class AgentUiRuntimeOperationRequest(StrictSchema):
    operation: Literal["prepare_case", "execute_node", "cleanup_case"]
    idempotency_key: str = Field(min_length=8, max_length=128)
    step_index: int | None = Field(default=None, ge=0)
    node_id: int | None = Field(default=None, gt=0)
    runtime_variables: dict[str, Any] = Field(default_factory=dict, max_length=10_000)
    client_result: dict[str, Any] = Field(default_factory=dict, max_length=100)


__all__ = [
    "AgentUiAssertionResult",
    "AgentUiCapabilityManifest",
    "AgentUiCompletionReport",
    "AgentUiCompletionStep",
    "AgentUiEvidencePolicy",
    "AgentUiRuntimeOperationRequest",
    "AgentUiStepReport",
    "AgentUiToolCallSummary",
]
