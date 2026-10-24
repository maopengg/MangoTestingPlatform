from pydantic import Field

from src.common.schemas import StrictSchema


class ExecutionCaseCommand(StrictSchema):
    test_suite_details: int
    test_suite: int
    case_id: int
    case_name: str
    test_env: int
    user_id: int
    tasks_id: int | None = None
    parametrize: list[dict] = Field(default_factory=list)
    case_revision_id: int | None = None
    case_release_id: int | None = None
    config_checksum: str | None = None


__all__ = ["ExecutionCaseCommand"]
