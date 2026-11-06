from pydantic import Field, field_validator, model_validator

from src.apps.data_factory.enums.performance import (
    DatasourcePermitKindEnum, DatasourcePermitStateEnum, DatasourceQueueLaneEnum,
)
from src.common.schemas import StrictSchema
from src.apps.test_center.enums.case import ReportFailureReasonEnum


class DatasourceTypeBudget(StrictSchema):
    cleanup_backlog_limit: int = Field(default=100, ge=1, le=10000)
    concurrency: int = Field(default=6, ge=2, le=64)
    requests_per_second: int = Field(default=30, ge=2, le=1000)
    connections: int = Field(default=12, ge=2, le=128)
    cleanup_reserved: int = Field(default=2, ge=1, le=32)
    cleanup_rate_percent: int = Field(default=25, ge=1, le=90)
    metadata_per_second: int = Field(default=2, ge=1, le=10)

    @model_validator(mode='after')
    def valid_reservation(self):
        if self.cleanup_reserved >= self.concurrency or self.metadata_per_second > self.requests_per_second:
            raise ValueError('清理保留并发必须小于总并发，元数据速率不能超过总速率')
        return self


class DatasourcePerformancePolicy(StrictSchema):
    version: int = Field(default=1, ge=1, le=1)
    mysql: DatasourceTypeBudget = Field(default_factory=DatasourceTypeBudget)
    redis: DatasourceTypeBudget = Field(default_factory=lambda: DatasourceTypeBudget(
        concurrency=12, requests_per_second=75, connections=16))
    elasticsearch: DatasourceTypeBudget = Field(default_factory=lambda: DatasourceTypeBudget(
        requests_per_second=15))
    queue_timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_waiters: int = Field(default=256, ge=1, le=256)
    permit_lease_seconds: int = Field(default=300, ge=30, le=3600)
    pool_size: int = Field(default=3, ge=1, le=8)
    transaction_statement_budget: int = Field(default=8, ge=2, le=64)
    pool_idle_seconds: int = Field(default=60, ge=5, le=600)
    max_local_pools: int = Field(default=32, ge=1, le=128)
    cleanup_completion_seconds: int = Field(default=300, ge=60, le=3600)
    cleanup_consumer_threads: int = Field(default=2, ge=1, le=16)

    @model_validator(mode='after')
    def reserve_cleanup_connections(self):
        if any(budget.connections <= self.pool_size for budget in
               [self.mysql, self.redis, self.elasticsearch]):
            raise ValueError('实例连接上限必须大于每池连接数，以保留清理连接容量')
        return self


class DatasourcePermit(StrictSchema):
    owner: str = Field(max_length=96)
    process: str = Field(max_length=128)
    lane: DatasourceQueueLaneEnum
    kind: DatasourcePermitKindEnum
    state: DatasourcePermitStateEnum = DatasourcePermitStateEnum.ACTIVE
    expires_at: float
    slots: int = Field(default=1, ge=1, le=128)
    case_detail_id: int | None = Field(default=None, ge=1)
    case_attempt: int | None = Field(default=None, ge=1)


class DatasourceWaiter(StrictSchema):
    lane: DatasourceQueueLaneEnum
    kind: DatasourcePermitKindEnum = DatasourcePermitKindEnum.OPERATION
    created_at: float
    expires_at: float


class DatasourceAdmissionInfo(StrictSchema):
    instance_group: str = Field(min_length=32, max_length=32)
    policy_version: str = Field(min_length=32, max_length=32)
    queue_lane: DatasourceQueueLaneEnum
    admission_wait_ms: float = Field(ge=0)
    attempt: int = Field(default=1, ge=1)


class DatasourceInfrastructureIssue(StrictSchema):
    code: int
    message: str = Field(max_length=1000)
    origin: ReportFailureReasonEnum = ReportFailureReasonEnum.PLATFORM

    @field_validator('origin', mode='before')
    @classmethod
    def parse_origin(cls, value):
        return ReportFailureReasonEnum(value)


class DatasourcePermitReviewReceipt(StrictSchema):
    reviewed_by: str = Field(min_length=1, max_length=64)
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviewed_at: float
    kind: DatasourcePermitKindEnum
    process: str = Field(max_length=128)


class DatasourceGovernorState(StrictSchema):
    version: int = Field(default=1, ge=1, le=1)
    updated_at: float = 0
    tokens: float = 0
    normal_tokens: float = 0
    metadata_tokens: float = 0
    permits: dict[str, DatasourcePermit] = Field(default_factory=dict, max_length=256)
    waiters: dict[str, DatasourceWaiter] = Field(default_factory=dict, max_length=256)
    admitted: int = 0
    throttled: int = 0
    completed: int = 0


class DatasourcePermitReview(StrictSchema):
    instance_group: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_permit: DatasourcePermit
    reviewed_by: str = Field(min_length=1, max_length=64)
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    physical_connection_closed: bool = Field(default=False, strict=True)
    operation_result_verified: bool = Field(default=False, strict=True)
    cleanup_verified: bool = Field(default=False, strict=True)
