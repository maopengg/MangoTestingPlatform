from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from src.common.schemas.base import StrictSchema
from .mapping import EvaluationMapping, normalize_output_paths
from .target import EvaluationTargetBinding
from .answer import EvaluationAnswering, EvaluationAssessment
from .answer import EvaluationAiSelection


class EvaluationGraderBinding(StrictSchema):
    grader_key: str = Field(min_length=1, max_length=64)
    grader_version: int = Field(default=1, ge=1)
    metric_key: str = Field(min_length=1, max_length=64)
    weight: float = Field(default=1, ge=0, allow_inf_nan=False)
    threshold: float = Field(default=80, ge=0, le=100, allow_inf_nan=False)
    hard_gate: bool = False
    enabled: bool = True
    parameters: dict = Field(default_factory=dict)

    @field_validator("grader_key", "metric_key")
    @classmethod
    def non_empty(cls, value):
        if not value.strip():
            raise ValueError("不能为空")
        return value.strip()


class EvaluationItemGrading(StrictSchema):
    schema_version: Literal[1] = 1
    mode: Literal["inherit", "replace"] = "inherit"
    graders: list[EvaluationGraderBinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode == "inherit" and self.graders:
            raise ValueError("继承模式不能声明评分覆盖")
        if self.mode == "replace" and not any(item.enabled for item in self.graders):
            raise ValueError("替换模式至少需要一个启用的评分项")
        return self


class EvaluationAggregation(StrictSchema):
    policy_version: Literal[2] = 2
    min_valid_rate: float = Field(default=0.95, gt=0, le=1, allow_inf_nan=False)
    min_effect_pass_rate: float = Field(default=0.8, ge=0, le=1, allow_inf_nan=False)


class EvaluationQualityGate(StrictSchema):
    key: str
    metric_key: str | None = None
    operator: Literal["gte", "gt", "lte", "lt", "eq", "zero"] = "gte"
    threshold: float = Field(default=0, allow_inf_nan=False)
    severity: Literal["critical", "warning"] = "critical"
    group_by: str | None = None


class EvaluationExecutionPolicy(StrictSchema):
    max_concurrency: int = Field(default=1, ge=1, le=20)
    item_timeout_seconds: int = Field(default=600, ge=1, le=3600)
    retry_count: int = Field(default=0, ge=0, le=3)
    repeat_count: int = Field(default=1, ge=1, le=10)
    stop_on_critical_failure: bool = False


class EvaluationGradingConfig(StrictSchema):
    default_graders: list[EvaluationGraderBinding] = Field(default_factory=list)
    required_graders: list[EvaluationGraderBinding] = Field(default_factory=list)
    aggregation: EvaluationAggregation = Field(default_factory=EvaluationAggregation)
    quality_gates: list[EvaluationQualityGate] = Field(default_factory=list)


class EvaluationDataSelection(StrictSchema):
    input_variable: str = Field(default="case_input", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$", exclude=True)
    exclude: bool = Field(default=False, strict=True)
    item_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(default_factory=list, max_length=10000)

    @field_validator("item_ids")
    @classmethod
    def validate_keys(cls, values):
        if any(isinstance(value, bool) or value <= 0 for value in values) or len(values) != len(set(values)):
            raise ValueError("条目 ID 必须为正整数且不能重复")
        return values


class EvaluationCaseMapping(StrictSchema):
    output: EvaluationMapping = Field(default_factory=EvaluationMapping)


class EvaluationCaseConfig(StrictSchema):
    ai: EvaluationAiSelection = Field(default_factory=EvaluationAiSelection)
    schema_version: Literal[1] = 1
    data_selection: EvaluationDataSelection = Field(default_factory=EvaluationDataSelection)
    target: EvaluationTargetBinding
    mapping: EvaluationCaseMapping = Field(default_factory=EvaluationCaseMapping)
    grading: EvaluationGradingConfig
    execution: EvaluationExecutionPolicy = Field(default_factory=EvaluationExecutionPolicy)
    assessment: EvaluationAssessment | None = None
    answering: EvaluationAnswering | None = None

    @model_validator(mode="before")
    @classmethod
    def discard_removed_preparation(cls, value):
        if isinstance(value, dict):
            value = {key: item for key, item in value.items() if key != "runtime_context"}
            if isinstance(value.get("grading"), dict):
                value["grading"] = dict(value["grading"])
                aggregation = value["grading"].get("aggregation")
                if isinstance(aggregation, dict):
                    value["grading"]["aggregation"] = {key: item for key, item in aggregation.items() if key not in {"pass_score", "warning_score", "invalid_policy"}}
            if isinstance(value.get("mapping"), dict):
                value["mapping"] = {key: item for key, item in value["mapping"].items() if key != "input"}
                output = value["mapping"].get("output", {})
                aliases = list((output.get("selectors") or {}).keys()) + list((output.get("collections") or {}).keys())
                value["mapping"]["output"] = normalize_output_paths(output)
                if aliases and isinstance(value.get("grading"), dict):
                    value["grading"] = dict(value["grading"])
                    for group in ("default_graders", "required_graders"):
                        bindings = []
                        for binding in value["grading"].get(group, []):
                            binding = {**binding, "parameters": dict(binding.get("parameters") or {})}
                            path = binding["parameters"].get("actual_path")
                            parts = path.removeprefix("$.").split(".") if isinstance(path, str) else []
                            if parts and parts[0] in aliases:
                                prefix = [] if len(aliases) == 1 else [str(aliases.index(parts[0]))]
                                binding["parameters"]["actual_path"] = ".".join(prefix + parts[1:])
                            bindings.append(binding)
                        value["grading"][group] = bindings
            if isinstance(value.get("answering"), dict):
                value["answering"] = {key: item for key, item in value["answering"].items() if key != "memories_path"}
        return value
