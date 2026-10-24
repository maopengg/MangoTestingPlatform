from pydantic import Field, StrictStr
from src.common.schemas.base import StrictSchema


class EvaluationAssessment(StrictSchema):
    objective: str = Field(min_length=1, max_length=1000)
    scope: list[str] = Field(default_factory=list, max_length=20)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    score_interpretation: str = Field(min_length=1, max_length=2000)


class EvaluationAnswering(StrictSchema):
    question_path: str = Field(default="query", min_length=1, max_length=512)
    max_tokens: int = Field(default=800, ge=100, le=8000)


class EvaluationAnswerModelSnapshot(StrictSchema):
    profile_id: str | None = None
    name: str | None = None
    config_hash: str | None = None
    provider: str
    model: str
    endpoint_hash: str
    prompt_version: int


class EvaluationAnswerOutput(StrictSchema):
    answer: StrictStr


class EvaluationAiSelection(StrictSchema):
    judge_profile_id: str | None = Field(default=None, min_length=1, max_length=64)
    summary_profile_id: str | None = Field(default=None, min_length=1, max_length=64)
    answer_profile_id: str | None = Field(default=None, min_length=1, max_length=64)


class EvaluationAiSummary(StrictSchema):
    overview: str = Field(min_length=1, max_length=2000)
    findings: list[str] = Field(default_factory=list, max_length=10)
    recommendations: list[str] = Field(default_factory=list, max_length=10)
