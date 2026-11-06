from pydantic import Field

from src.common.schemas import StrictSchema


class ServerTaskLease(StrictSchema):
    task_id: int
    token: str
    generation: int
    recovered: bool
    payload: dict
    progress: dict = Field(default_factory=dict)
