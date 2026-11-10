from pydantic import Field

from src.common.schemas import FrozenSchema


class McpConfirmationBindingSchema(FrozenSchema):
    user_id: int = Field(strict=True, gt=0)
    action: str = Field(strict=True, min_length=1)
    target_id: str = Field(strict=True, min_length=1)
    confirm_text: str = Field(strict=True, min_length=1)
