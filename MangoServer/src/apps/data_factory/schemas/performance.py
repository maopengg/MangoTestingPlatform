from pydantic import Field, ValidationInfo, field_validator, model_serializer, model_validator

from src.apps.data_factory.enums.performance import (
    DatasourcePermitKindEnum, DatasourcePermitStateEnum, DatasourceQueueLaneEnum,
)
from src.common.schemas import StrictSchema
from src.apps.test_center.enums.case import ReportFailureReasonEnum
from typing import Literal


class DatasourceTypeBudget(StrictSchema):
    connections: int = Field(default=12, ge=2, le=128)


class DatasourcePerformancePolicy(StrictSchema):
    version: int = Field(default=2, ge=2, le=2)
    mysql: DatasourceTypeBudget = Field(default_factory=lambda: DatasourceTypeBudget(connections=20))
    redis: DatasourceTypeBudget = Field(default_factory=lambda: DatasourceTypeBudget(connections=16))
    elasticsearch: DatasourceTypeBudget = Field(default_factory=DatasourceTypeBudget)
    pool_size: int = Field(default=4, ge=1, le=8)
    pool_idle_seconds: int = Field(default=60, ge=5, le=600)
    max_local_pools: int = Field(default=32, ge=1, le=128)
    cleanup_completion_seconds: int = Field(default=300, ge=60, le=3600)
    cleanup_consumer_threads: int = Field(default=2, ge=1, le=16)

    @field_validator('mysql', 'redis', 'elasticsearch', mode='before')
    @classmethod
    def complete_type_defaults(cls, value, info: ValidationInfo):
        if isinstance(value, dict):
            default = cls.model_fields[info.field_name].get_default(call_default_factory=True)
            return {'connections': default.connections, **value}
        return value

    @model_validator(mode='after')
    def reserve_cleanup_connections(self):
        if any(budget.connections <= self.pool_size for budget in
               (self.mysql, self.redis, self.elasticsearch)):
            raise ValueError('实例连接总数必须大于每池连接数，以保留清理连接容量')
        return self


class MysqlOperationSession(StrictSchema):
    server_uuid: str = Field(pattern=r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    session_id: int = Field(ge=1)
    target_key: str = Field(pattern=r'^[a-f0-9]{40}$')
    account_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


class MysqlSessionRecoveryEvidence(StrictSchema):
    owner: str = Field(pattern=r'^[a-f0-9]{32}$')
    session_id: int = Field(ge=1)
    server_uuid: str = Field(pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    checked_at: float = Field(ge=0)
    basis: Literal['server_session_absent'] = 'server_session_absent'


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
    audit_record_id: int | None = Field(default=None, ge=1)
    audit_request_id: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: float | None = Field(default=None, ge=0)
    unknown_since: float | None = Field(default=None, ge=0)
    mysql_session: MysqlOperationSession | None = None
    recovery_checked_at: float | None = Field(default=None, ge=0)

    @model_serializer(mode='wrap')
    def compact_optional_evidence(self, handler):
        data = handler(self)
        for key in ('audit_record_id', 'audit_request_id', 'created_at', 'unknown_since', 'mysql_session', 'recovery_checked_at'):
            if data.get(key) is None:
                data.pop(key, None)
        return data


class DatasourceOperationCompletion(StrictSchema):
    """平台物理操作上下文的终结证明；不代表事务提交或资源清理完成。"""
    group: str = Field(pattern=r'^[a-f0-9]{32}$')
    owner: str = Field(pattern=r'^[a-f0-9]{32}$')
    process: str = Field(max_length=128)
    confirmed_at: float = Field(ge=0)


class DatasourceConnectionClosure(StrictSchema):
    """物理 close 或同服务器会话不存在的证明，不表示业务操作或清理成功。"""
    group: str = Field(pattern=r'^[a-f0-9]{32}$')
    owner: str = Field(pattern=r'^[a-f0-9]{32}$')
    process: str = Field(min_length=1, max_length=128)
    confirmed_at: float = Field(ge=0)
    basis: Literal['physical_close', 'server_session_absent'] = 'physical_close'
    mysql_session: MysqlOperationSession | None = None

    @model_validator(mode='after')
    def require_session_for_probe(self):
        if self.basis == 'server_session_absent' and self.mysql_session is None:
            raise ValueError('会话不存在证明必须包含原始MySQL会话身份')
        return self

    @model_serializer(mode='wrap')
    def compact_close_proof(self, handler):
        data = handler(self)
        if self.basis == 'physical_close':
            data.pop('basis', None)
            data.pop('mysql_session', None)
        return data


class DatasourceInfrastructureIssue(StrictSchema):
    code: int
    message: str = Field(max_length=1000)
    origin: ReportFailureReasonEnum = ReportFailureReasonEnum.PLATFORM
    request_id: str | None = Field(default=None, max_length=128)
    permit_owner: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')

    @field_validator('origin', mode='before')
    @classmethod
    def parse_origin(cls, value):
        return ReportFailureReasonEnum(value)


class DatasourceHealthMetrics(StrictSchema):
    waiting_count: int = Field(default=0, ge=0)
    unconfirmed_count: int = Field(default=0, ge=0)
    unsettled_count: int = Field(default=0, ge=0)
    wait_seconds: float = Field(default=0, ge=0)
    no_completion_seconds: float = Field(default=0, ge=0)
    no_progress_seconds: float = Field(default=0, ge=0)
    report_ids: list[int] = Field(default_factory=list, max_length=10)
    detail_ids: list[int] = Field(default_factory=list, max_length=10)
    case_ids: list[int] = Field(default_factory=list, max_length=10)
    audit_ids: list[int] = Field(default_factory=list, max_length=10)


class DatasourceReportProgress(StrictSchema):
    report_id: int = Field(ge=1)
    terminal_count: int = Field(ge=0)
    last_progress_at: float = Field(ge=0)
    last_completion_at: float = Field(default=0, ge=0)


class DatasourceHealthIncident(StrictSchema):
    scope: str = Field(default='', max_length=256)
    worker: bool = False
    generation: float = Field(default=0, ge=0)
    active: bool = False
    revision: int = Field(default=0, ge=0)
    delivered_revision: int = Field(default=0, ge=0)
    occurrences: int = Field(default=0, ge=0)
    opened_at: float | None = Field(default=None, ge=0)
    resolved_at: float | None = Field(default=None, ge=0)
    last_seen_at: float = Field(default=0, ge=0)
    publisher: str | None = Field(default=None, max_length=32)
    publish_until: float = Field(default=0, ge=0)
    metrics: DatasourceHealthMetrics = Field(default_factory=DatasourceHealthMetrics)


class DatasourcePermitReviewReceipt(StrictSchema):
    reviewed_by: str = Field(min_length=1, max_length=64)
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviewed_at: float
    kind: DatasourcePermitKindEnum
    process: str = Field(max_length=128)


class DatasourceGovernorState(StrictSchema):
    version: int = Field(default=2, ge=2, le=2)
    recovery_owner: str | None = Field(default=None, max_length=96)
    recovery_until: float = Field(default=0, ge=0)
    recovery_next_at: float = Field(default=0, ge=0)
    connection_wait_until: float = 0
    connection_wait_since: float = 0
    permits: dict[str, DatasourcePermit] = Field(default_factory=dict, max_length=512)
    admitted: int = 0
    completed: int = 0


class DatasourcePermitReview(StrictSchema):
    instance_group: str = Field(pattern=r'^[a-f0-9]{32}$')
    expected_permit: DatasourcePermit
    reviewed_by: str = Field(min_length=1, max_length=64)
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    physical_connection_closed: bool = Field(default=False, strict=True)
    operation_result_verified: bool = Field(default=False, strict=True)
    cleanup_verified: bool = Field(default=False, strict=True)
