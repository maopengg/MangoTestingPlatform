from pydantic import Field
from src.common.schemas.base import StrictSchema


class EvaluationInterfaceSelection(StrictSchema):
    module_id: int | None = Field(default=None, gt=0)
    selected_id: int | None = Field(default=None, gt=0)
    search: str = Field(default="", max_length=200)
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=50, ge=1, le=100)
