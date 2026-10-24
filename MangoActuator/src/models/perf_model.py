from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PerfStage(StrictModel):
    stage_key: str
    name: str
    duration_seconds: int = Field(ge=1)
    target_users: int | None = Field(default=None, ge=1)
    target_rate: float | None = Field(default=None, gt=0)
    rate_time_unit: Literal["second", "minute"] | None = None
    preallocated_vus: int | None = Field(default=None, ge=1)
    max_vus: int | None = Field(default=None, ge=1)
    ramp_type: Literal["step", "linear"] = "linear"
    spawn_rate: float | None = Field(default=None, gt=0)


class PerfStep(StrictModel):
    step_key: str
    name: str
    sort: int
    weight: int = Field(default=1, ge=1)
    think_time_ms: int = Field(default=0, ge=0)
    api_info_id: int
    api_revision_id: int
    api_revision_checksum: str
    request: dict[str, Any]
    request_override: dict[str, Any] = Field(default_factory=dict)
    extractors: list[dict[str, Any]] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    retries: int = Field(default=0, ge=0, le=10)
    retry_interval_ms: int = Field(default=0, ge=0)
    allow_failure: bool = False


class PerfCaseVariable(StrictModel):
    key: str
    value: Any = None
    test_envs: list[int] = Field(default_factory=list)


class PerfPerformanceGoal(StrictModel):
    template_key: Literal["recommended", "custom"] = "recommended"
    p95_ms: int = Field(default=500, ge=1)
    max_error_rate: float = Field(default=0.01, ge=0, le=1)
    min_load_achievement_rate: float = Field(default=0.95, ge=0, le=1)


class PerfFunction(StrictModel):
    expression: str
    name: str
    args: dict[str, str | int] = Field(default_factory=dict)
    cache_key: str | None = None


class PerfScenario(StrictModel):
    schema_version: Literal[1, 2]
    scenario_id: int
    scenario_version: int
    name: str
    project_product_id: int
    module_id: int
    engine: Literal["k6"]
    source_case_id: int
    source_case_release_id: int
    source_case_revision_id: int
    source_case_revision_checksum: str
    source_case_version_label: str
    test_env: int | None = None
    initial_variables: list[PerfCaseVariable] = Field(default_factory=list)
    perf_functions: list[PerfFunction] = Field(default_factory=list)
    execution_mode: Literal["sequential"] = "sequential"
    load_type: Literal["concurrency", "arrival_rate", "iteration_rate"]
    load_profile: Literal["constant_concurrency", "fixed_iterations", "staircase", "linear_ramp", "spike", "soak", "constant_arrival_rate", "constant_iteration_rate"] = "constant_concurrency"
    total_iterations: int | None = Field(default=None, ge=1)
    start_users: int | None = Field(default=None, ge=0)
    user_wait_min_ms: int = Field(ge=0)
    user_wait_max_ms: int = Field(ge=0)
    steps: list[PerfStep] = Field(min_length=1)
    stages: list[PerfStage] = Field(min_length=1)
    performance_goal: PerfPerformanceGoal


class PerfExecutionRequest(StrictModel):
    run_id: int
    run_node_id: int
    node_key: str
    schedule_at: datetime
    schedule_at_epoch_ms: int | None = Field(default=None, gt=0)
    scenario: PerfScenario
    variables: dict[str, Any] = Field(default_factory=dict)
    shard_index: int = Field(ge=0)
    shard_count: int = Field(ge=1)
    capture: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shard(self):
        if self.shard_index >= self.shard_count:
            raise ValueError("分片索引必须小于分片总数")
        return self
