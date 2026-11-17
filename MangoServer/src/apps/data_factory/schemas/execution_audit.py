from typing import Literal

from pydantic import Field

from src.common.schemas import FrozenSchema
from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum


class DatasourceAuditOrigin(FrozenSchema):
    case_id: int | None = Field(default=None, ge=1)
    test_suite_id: int | None = Field(default=None, ge=1)
    test_suite_detail_id: int | None = Field(default=None, ge=1)
    trace_id: str | None = Field(default=None, max_length=64)


class DatasourceAuditMetadata(FrozenSchema):
    """source_detail 中通用目标快照；其余业务来源仍由各调用方构造。"""

    target_kind: Literal['connection', 'logical_database']
    database_name: str = Field(default='', max_length=128)
    redis_db: int | None = Field(default=None, ge=0)
    index: str | None = Field(default=None, max_length=1024)
    operation: str = Field(max_length=64)
    case_detail_id: int | None = Field(default=None, ge=1)
    case_attempt: int | None = Field(default=None, ge=1)
    case_id: int | None = Field(default=None, ge=1)
    test_suite_id: int | None = Field(default=None, ge=1)
    test_suite_detail_id: int | None = Field(default=None, ge=1)
    started_at: str | None = None
    finished_at: str | None = None
    parent_request_id: str | None = Field(default=None, max_length=64)
    request_claimed: bool = False
    result_fully_read: bool | None = None
    transaction_outcome: Literal['rolled_back', 'unknown'] | None = None
    resource_wait_ms: float = Field(default=0, ge=0)
    factory_preparation_ms: float = Field(default=0, ge=0)
    factory_preparation_wait_ms: float = Field(default=0, ge=0)
    driver_error_number: int | None = Field(default=None, ge=0)
    # 各段互斥累计毫秒数；父审计包含其子操作，统计时不可父子相加。
    timing_ms: dict[DatasourceTimingPhaseEnum, float] = Field(default_factory=dict)
    factory_preparation_timing_ms: dict[DatasourceTimingPhaseEnum, float] = Field(default_factory=dict)


class DatasourceAuditRequestClaim(FrozenSchema):
    """显式请求编号的持久去重凭据；不是配额，不自动过期或重放。"""

    request_id: str = Field(min_length=1, max_length=64)
    signature: str = Field(pattern=r'^[a-f0-9]{64}$')
    owner: str = Field(min_length=1, max_length=128)
    created_at: str
