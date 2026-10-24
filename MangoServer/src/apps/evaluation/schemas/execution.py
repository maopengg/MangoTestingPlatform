from typing import Annotated, Literal
from pydantic import Field
from src.common.schemas.base import StrictSchema
from .case import EvaluationCaseMapping, EvaluationExecutionPolicy, EvaluationGradingConfig, EvaluationGraderBinding
from .answer import EvaluationAnswering, EvaluationAssessment, EvaluationAnswerModelSnapshot
from .dataset import EvaluationDatasetSchema
from .workflow import EvaluationWorkflowRecord


class EvaluationCaseExecutionCreate(StrictSchema):
    case_id: int = Field(gt=0)
    test_env: int = Field(gt=0)
    trigger_type: Literal["manual", "api"] = "manual"
    item_ids: list[Annotated[int, Field(strict=True, gt=0)]] | None = Field(default=None, max_length=10000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=160)


class EvaluationExecutionDetails(StrictSchema):
    schema_version: Literal[1] = 1
    error_category: str | None = None
    error_message: str | None = None
    diagnostic_ref: dict = Field(default_factory=dict)
    workflow: list[EvaluationWorkflowRecord] = Field(default_factory=list)
    cleanup_errors: list[str] = Field(default_factory=list)


class EvaluationExecutionSnapshot(StrictSchema):
    schema_version: Literal[1] = 1
    hash_version: Literal[1] = 1
    case: dict
    dataset: dict
    selection: dict
    target: dict
    mapping: EvaluationCaseMapping
    grader_bindings: dict[str, EvaluationGraderBinding]
    grader_implementations: dict[str, str]
    grading: EvaluationGradingConfig
    execution: EvaluationExecutionPolicy
    environment: dict
    request: dict
    signatures: dict
    input_variable: str = Field(default="case_input", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    dataset_config: EvaluationDatasetSchema = Field(default_factory=EvaluationDatasetSchema)
    assessment: EvaluationAssessment | None = None
    answering: EvaluationAnswering | None = None
    answer_model: EvaluationAnswerModelSnapshot | None = None
    summary_model: EvaluationAnswerModelSnapshot | None = None
