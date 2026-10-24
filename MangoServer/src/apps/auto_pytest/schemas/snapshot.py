from src.common.schemas import StrictSchema


class PytestSourceSnapshot(StrictSchema):
    version: int = 1
    repository_id: int
    repository_name: str
    pytest_project_id: int
    pytest_project_name: str | None = None
    branch: str | None = None
    commit_hash: str
    project_path: str
    working_directory: str
    pytest_config_path: str | None = None
    file_path: str
    nodeid: str | None = None


__all__ = ["PytestSourceSnapshot"]
