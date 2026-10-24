from pydantic import Field

from src.common.schemas import StrictSchema


class FrontendErrorReport(StrictSchema):
    operation: str = Field(min_length=1, max_length=255)
    exception_type: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=500)
    traceback: str | None = Field(default=None, max_length=50000)


__all__ = ["FrontendErrorReport"]
