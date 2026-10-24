from src.common.schemas import StrictSchema


class CaseCounter(StrictSchema):
    case_sum: int = 0
    step_sum: int = 0
    success: int = 0
    fail: int = 0
    warning: int = 0


__all__ = ["CaseCounter"]
