from typing import Any
from pydantic import Field, StrictBool, StrictStr, ConfigDict
from src.common.schemas.base import StrictSchema


class GraderMetric(StrictSchema):
    key: str
    raw_value: Any = None
    score: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    passed: bool
    evidence: dict = Field(default_factory=dict)
    reason: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)


class GraderResult(StrictSchema):
    metrics: list[GraderMetric] = Field(min_length=1)
    requires_review: bool = False


class ModelJudgeOutput(StrictSchema):
    model_config = ConfigDict(extra="forbid", strict=True)
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    passed: StrictBool
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    requires_review: StrictBool
    reason: StrictStr
    evidence: dict
