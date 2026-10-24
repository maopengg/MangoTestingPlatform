from pydantic import Field, StrictBool, StrictStr
from src.common.schemas.base import StrictSchema
from src.apps.evaluation.enums.memory import MemoryFactStatusEnum


class MemoryFactCheck(StrictSchema):
    index: int = Field(ge=0, strict=True)
    status: MemoryFactStatusEnum
    actual_quote: StrictStr
    source_quote: StrictStr
    reason: str = Field(min_length=1)


class MemoryJudgment(StrictSchema):
    expected_checks: list[MemoryFactCheck]
    actual_checks: list[MemoryFactCheck]
    requires_review: StrictBool
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)
    reason: str = Field(min_length=1)
