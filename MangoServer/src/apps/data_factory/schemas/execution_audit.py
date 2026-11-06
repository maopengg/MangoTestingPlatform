from typing import Literal

from pydantic import Field

from src.common.schemas import FrozenSchema


class DatasourceAuditMetadata(FrozenSchema):
    """source_detail 中通用目标快照；其余业务来源仍由各调用方构造。"""

    target_kind: Literal['connection', 'logical_database']
    database_name: str = Field(default='', max_length=128)
    redis_db: int | None = Field(default=None, ge=0)
    index: str | None = Field(default=None, max_length=1024)
    operation: str = Field(max_length=64)
    resource_wait_ms: float = Field(default=0, ge=0)
    transaction_admission_wait_ms: float = Field(default=0, ge=0)
    factory_preparation_ms: float = Field(default=0, ge=0)
    factory_preparation_wait_ms: float = Field(default=0, ge=0)
