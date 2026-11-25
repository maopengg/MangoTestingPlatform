from datetime import datetime
from pydantic import Field

from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum, ReportRecoveryCauseEnum, ReportRecoveryActionEnum, ReportRecoveryReasonEnum
from src.common.schemas import StrictSchema


class ReportInfrastructureBlock(StrictSchema):
    phase: ReportExecutionPhaseEnum = ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED
    attempt: int = Field(ge=1)
    observed_at: str
    issues: list[DatasourceInfrastructureIssue] = Field(default_factory=list)
    requires_review: bool = True
    reviewed_by: int | None = None
    reviewed_at: str | None = None


class ReportRecoveryControl(StrictSchema):
    version: int = Field(default=2, ge=2, le=2)
    phase: ReportExecutionPhaseEnum = ReportExecutionPhaseEnum.AUTOMATIC_RECOVERY
    attempt: int = Field(ge=1)
    cause: ReportRecoveryCauseEnum
    action: ReportRecoveryActionEnum
    observed_at: datetime
    next_check_at: datetime
    deadline_at: datetime
    owner_ended: bool = False
    checks: int = Field(default=0, ge=0)
    issues: list[DatasourceInfrastructureIssue] = Field(default_factory=list, max_length=100)
    reason: ReportRecoveryReasonEnum | None = None
    exception_recorded: bool = False
    result_expected: bool = False
    result_id: int | None = Field(default=None, ge=1)
