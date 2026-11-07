from pydantic import Field

from src.common.schemas import StrictSchema


class MonitoringScriptCapabilities(StrictSchema):
    version: int = 1
    python_version: str = Field(max_length=32)
    packages: dict[str, str | None]
