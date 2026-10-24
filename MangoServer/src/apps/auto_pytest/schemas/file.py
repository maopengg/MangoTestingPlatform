from datetime import datetime

from pydantic import Field

from src.common.schemas import StrictSchema


class PytestFileSchema(StrictSchema):
    name: str
    path: str
    time: datetime


class PytestFileUpdateCommand(StrictSchema):
    project_name: str
    auto_test: list[PytestFileSchema] = Field(default_factory=list)
    init_file_path: str
    module_name: list[str] = Field(default_factory=list)


__all__ = ["PytestFileSchema", "PytestFileUpdateCommand"]
