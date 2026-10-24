from datetime import datetime
from pydantic import Field, JsonValue
from src.apps.evaluation.enums import EvaluationExecutionStatusEnum
from src.common.schemas.base import StrictSchema


class EvaluationAttemptRecord(StrictSchema):
    attempt_no: int = Field(ge=1)
    status: EvaluationExecutionStatusEnum
    create_time: datetime
    update_time: datetime
    duration_ms: int | None = Field(default=None, ge=0)
    output_snapshot: JsonValue = Field(default_factory=dict)
    execution_ref: dict = Field(default_factory=dict)
    error_category: str | None = None
    error_message: str | None = None
