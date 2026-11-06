from pydantic import Field

from src.common.schemas import StrictSchema


class ApiWorkerClaimOwner(StrictSchema):
    worker_name: str = Field(min_length=1, max_length=128)
    process_token: str = Field(pattern=r'^[a-f0-9]{32}$')
    process_started_at: str = Field(min_length=1, max_length=64)


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
    attempt: int = 1


__all__ = ["ExecutionCaseCommand"]
