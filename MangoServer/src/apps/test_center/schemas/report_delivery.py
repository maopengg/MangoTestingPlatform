from pydantic import ConfigDict, Field
from src.common.schemas.base import StrictSchema


class ReportDeliveryConfig(StrictSchema):
    model_config = ConfigDict(extra='forbid', validate_default=True)
    version: int = Field(default=1, ge=1, le=1)
    enabled: bool = False
    include_details: bool = True
    failed_cases_only: bool = True
    include_screenshots: bool = False
    link_ttl_seconds: int = Field(default=604800, ge=300, le=604800)
