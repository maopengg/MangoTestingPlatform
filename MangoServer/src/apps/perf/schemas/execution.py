from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from src.common.schemas import TrimmedStrictSchema


class PerfExecutorPolicy(TrimmedStrictSchema):
    mode: Literal["auto", "specified"] = "auto"
    specified_executor_fingerprints: list[str] = Field(default_factory=list, max_length=100)
    min_ready_nodes: int = Field(default=1, ge=1, le=100)
    capacity_safety_factor: float = Field(default=0.7, ge=0.1, le=1.0)
    node_failure_policy: Literal["strict", "continue"] = "strict"

    @model_validator(mode="after")
    def validate_selection(self):
        if self.mode == "specified" and not self.specified_executor_fingerprints:
            raise ValueError("指定执行器模式必须选择至少一个执行器")
        return self


class PerfRequestOverride(TrimmedStrictSchema):
    headers: dict[str, str] = Field(default_factory=dict, max_length=100)
    params: dict[str, Any] = Field(default_factory=dict, max_length=100)
    body: Any = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)


class PerfExtractor(TrimmedStrictSchema):
    name: str = Field(min_length=1, max_length=64)
    source: Literal["jsonpath", "regex", "header"]
    expression: str = Field(min_length=1, max_length=512)
    required: bool = True


class PerfCheck(TrimmedStrictSchema):
    source: Literal["status", "jsonpath", "regex", "header", "elapsed_ms", "json", "text", "variable"]
    expression: str = Field(default="", max_length=512)
    operator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains", "exists", "not_exists"]
    expected: Any = None


class PerfStageIR(TrimmedStrictSchema):
    stage_key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    duration_seconds: int = Field(ge=1, le=86400)
    target_users: int | None = Field(default=None, ge=1, le=1_000_000)
    target_rate: float | None = Field(default=None, gt=0, le=10_000_000)
    rate_time_unit: Literal["second", "minute"] | None = None
    preallocated_vus: int | None = Field(default=None, ge=1, le=1_000_000)
    max_vus: int | None = Field(default=None, ge=1, le=1_000_000)
    ramp_type: Literal["step", "linear"] = "linear"
    spawn_rate: float | None = Field(default=None, gt=0)


class PerfStepIR(TrimmedStrictSchema):
    step_key: str
    name: str
    sort: int = Field(ge=0)
    weight: int = Field(default=1, ge=1)
    think_time_ms: int = Field(default=0, ge=0, le=3_600_000)
    api_info_id: int
    api_revision_id: int
    api_revision_checksum: str
    request: dict[str, Any]
    request_override: PerfRequestOverride = Field(default_factory=PerfRequestOverride)
    extractors: list[PerfExtractor] = Field(default_factory=list, max_length=50)
    checks: list[PerfCheck] = Field(default_factory=list, max_length=50)
    retries: int = Field(default=0, ge=0, le=10)
    retry_interval_ms: int = Field(default=0, ge=0, le=600_000)
    allow_failure: bool = False


class PerfCaseVariableIR(TrimmedStrictSchema):
    key: str = Field(min_length=1, max_length=128)
    value: Any = None
    test_envs: list[int] = Field(default_factory=list, max_length=20)


class PerfPerformanceGoalIR(TrimmedStrictSchema):
    template_key: Literal["recommended", "custom"] = "recommended"
    p95_ms: int = Field(default=500, ge=1)
    max_error_rate: float = Field(default=0.01, ge=0, le=1)
    min_load_achievement_rate: float = Field(default=0.95, ge=0, le=1)


class PerfFunctionIR(TrimmedStrictSchema):
    expression: str
    name: str
    args: dict[str, str | int] = Field(default_factory=dict)
    cache_key: str | None = None


class PerfScenarioIR(TrimmedStrictSchema):
    schema_version: Literal[1, 2] = 1
    scenario_id: int
    scenario_version: int
    name: str
    project_product_id: int
    module_id: int
    engine: Literal["k6"]
    source_case_id: int
    source_case_release_id: int
    source_case_revision_id: int
    source_case_revision_checksum: str = Field(min_length=64, max_length=64)
    source_case_version_label: str
    test_env: int | None = None
    initial_variables: list[PerfCaseVariableIR] = Field(default_factory=list, max_length=500)
    perf_functions: list[PerfFunctionIR] = Field(default_factory=list, max_length=500)
    execution_mode: Literal["sequential"] = "sequential"
    load_type: Literal["concurrency", "arrival_rate", "iteration_rate"]
    load_profile: Literal[
        "constant_concurrency", "fixed_iterations", "staircase", "linear_ramp", "spike", "soak", "constant_arrival_rate", "constant_iteration_rate"] = "constant_concurrency"
    total_iterations: int | None = Field(default=None, ge=1)
    start_users: int | None = Field(default=None, ge=0)
    user_wait_min_ms: int = Field(ge=0)
    user_wait_max_ms: int = Field(ge=0)
    steps: list[PerfStepIR] = Field(min_length=1, max_length=500)
    stages: list[PerfStageIR] = Field(min_length=1, max_length=100)
    performance_goal: PerfPerformanceGoalIR = Field(default_factory=PerfPerformanceGoalIR)

    @model_validator(mode="after")
    def validate_load_model(self):
        if self.user_wait_min_ms > self.user_wait_max_ms:
            raise ValueError("最小思考时间不能大于最大思考时间")
        if self.load_profile == "fixed_iterations" and self.total_iterations is None:
            raise ValueError("定量任务必须配置 Case 执行次数")
        for stage in self.stages:
            if self.load_type == "concurrency" and stage.target_users is None:
                raise ValueError("并发用户模型的每个阶段都必须配置目标用户数")
            if self.load_type != "concurrency" and stage.target_rate is None:
                raise ValueError("开放负载模型的每个阶段都必须配置目标速率")
            if self.load_type == "concurrency":
                stage.target_rate = None
                stage.rate_time_unit = None
            else:
                stage.target_users = None
                if stage.rate_time_unit == "minute":
                    stage.target_rate = stage.target_rate / 60
                    stage.rate_time_unit = "second"
            if stage.max_vus and stage.preallocated_vus and stage.max_vus < stage.preallocated_vus:
                raise ValueError("最大 VU 不能小于预分配 VU")
        return self


class PerfLoadPoint(TrimmedStrictSchema):
    users: int | None = Field(default=None, ge=0)
    rate: float | None = Field(default=None, ge=0)
    iterations_per_second: float | None = Field(default=None, ge=0)


class PerfGeneratorMetrics(TrimmedStrictSchema):
    cpu_percent: float | None = Field(default=None, ge=0)
    memory_bytes: int | None = Field(default=None, ge=0)
    network_sent_bytes: int | None = Field(default=None, ge=0)
    network_received_bytes: int | None = Field(default=None, ge=0)
    outbox_items: int = Field(default=0, ge=0)
    event_loop_lag_ms: float | None = Field(default=None, ge=0)


class PerfTimingBreakdown(TrimmedStrictSchema):
    dns_ms: float | None = Field(default=None, ge=0)
    connect_ms: float | None = Field(default=None, ge=0)
    tls_ms: float | None = Field(default=None, ge=0)
    ttfb_ms: float | None = Field(default=None, ge=0)
    download_ms: float | None = Field(default=None, ge=0)


class PerfMetricPoint(TrimmedStrictSchema):
    sequence: int = Field(ge=1)
    window_start: datetime
    window_seconds: int = Field(ge=1, le=60)
    scope_type: Literal["global", "request", "stage", "node"]
    scope_key: str = Field(min_length=1, max_length=128)
    stage_key: str = Field(default="", max_length=64)
    target_load: PerfLoadPoint = Field(default_factory=PerfLoadPoint)
    actual_load: PerfLoadPoint = Field(default_factory=PerfLoadPoint)
    request_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    iteration_count: int = Field(default=0, ge=0)
    dropped_count: int = Field(default=0, ge=0)
    response_time_sum_ms: int = Field(default=0, ge=0)
    min_response_time_ms: int | None = Field(default=None, ge=0)
    max_response_time_ms: int | None = Field(default=None, ge=0)
    bytes_sent: int = Field(default=0, ge=0)
    bytes_received: int = Field(default=0, ge=0)
    connection_count: int = Field(default=0, ge=0)
    connect_error_count: int = Field(default=0, ge=0)
    histogram: str = Field(default="", max_length=1_000_000)
    timing_breakdown: PerfTimingBreakdown = Field(default_factory=PerfTimingBreakdown)
    generator_metrics: PerfGeneratorMetrics = Field(default_factory=PerfGeneratorMetrics)


class PerfMetricBatch(TrimmedStrictSchema):
    schema_version: Literal[1] = 1
    run_id: int
    run_node_id: int
    points: list[PerfMetricPoint] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_sequences(self):
        sequences = [point.sequence for point in self.points]
        if sequences != sorted(sequences):
            raise ValueError("指标序号必须单调递增")
        return self


class PerfErrorSamplePayload(TrimmedStrictSchema):
    sample_key: str = Field(min_length=8, max_length=64)
    occurred_at: datetime
    step_key: str = Field(default="", max_length=36)
    error_type: str = Field(min_length=1, max_length=64)
    error_code: str = Field(default="", max_length=64)
    message: str = Field(min_length=1, max_length=4096)
    request_summary: dict[str, Any] = Field(default_factory=dict)
    response_status: int | None = None
    response_excerpt: str = Field(default="", max_length=4096)
    elapsed_ms: int | None = Field(default=None, ge=0)


class PerfErrorBatch(TrimmedStrictSchema):
    schema_version: Literal[1] = 1
    run_id: int
    run_node_id: int
    samples: list[PerfErrorSamplePayload] = Field(min_length=1, max_length=100)
