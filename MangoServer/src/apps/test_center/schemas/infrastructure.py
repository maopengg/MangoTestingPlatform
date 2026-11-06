from pydantic import Field

from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.common.schemas import StrictSchema


class ReportInfrastructureBlock(StrictSchema):
    phase: ReportExecutionPhaseEnum = ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED
    attempt: int = Field(ge=1)
    observed_at: str
    issues: list[DatasourceInfrastructureIssue] = Field(default_factory=list)
    requires_review: bool = True
    reviewed_by: int | None = None
    reviewed_at: str | None = None
