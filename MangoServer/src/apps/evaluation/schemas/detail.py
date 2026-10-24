from typing import Literal
from pydantic import Field, JsonValue
from src.common.schemas.base import StrictSchema
from .workflow import EvaluationWorkflowRecord, EvaluationTurnResult


class EvaluationRuntimeReference(StrictSchema):
    key: str
    target_id: int
    content_hash: str
    output: dict
    record_count: int = Field(ge=0)


class EvaluationExecutionReferences(StrictSchema):
    oracle: dict = Field(default_factory=dict)
    fixture: dict = Field(default_factory=dict)
    raw_output: dict = Field(default_factory=dict)
    execution: dict = Field(default_factory=dict)
    runtime: list[EvaluationRuntimeReference] = Field(default_factory=list)


class EvaluationExecutionTiming(StrictSchema):
    execution_ms: int | None = Field(default=None, ge=0)
    grade_ms: int | None = Field(default=None, ge=0)


class EvaluationItemDetails(StrictSchema):
    schema_version: Literal[1] = 1
    references: EvaluationExecutionReferences = Field(default_factory=EvaluationExecutionReferences)
    timing: EvaluationExecutionTiming = Field(default_factory=EvaluationExecutionTiming)
    error_message: str | None = None
    cleanup_error: str | None = None
    workflow: list[EvaluationWorkflowRecord] = Field(default_factory=list)
    turns: list[EvaluationTurnResult] = Field(default_factory=list)


class EvaluationGradeSnapshot(StrictSchema):
    schema_version: Literal[1] = 1
    binding_hash: str
    metric: str = Field(min_length=1, max_length=64)
    threshold: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    weight: float = Field(default=1, ge=0, allow_inf_nan=False)
    turn_index: int = Field(default=0, ge=0)
