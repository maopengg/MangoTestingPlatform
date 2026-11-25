from datetime import datetime

from pydantic import BaseModel, Field, JsonValue, field_validator

from src.common.schemas import StrictSchema
from src.apps.data_factory.enums.cleanup_history import ResourceCleanupEventEnum


class CleanupEventEvidence(StrictSchema):
    message: str = ''
    sql_verified: bool | None = None
    es_verified: bool | None = None
    snapshot_digest: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    authorization_digest: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    compensation: dict[str, JsonValue] | None = None
    api_recovery: dict[str, JsonValue] | None = None
    checkpoints: list[dict[str, JsonValue]] = Field(default_factory=list, max_length=5)
    results: list[dict[str, JsonValue]] = Field(default_factory=list, max_length=5)

    @field_validator('compensation', 'api_recovery', 'checkpoints', 'results', mode='before')
    @classmethod
    def validate_details(cls, value, info):
        # 延迟解析以避免资源状态与内嵌历史的循环导入；仍按原严格 Schema 校验证据。
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCompensation, EsCleanupCheckpoint, EsCleanupCheckResult
        from src.apps.auto_api.schemas.resource_cleanup import ApiResourceRecoveryEvidence
        model = {'compensation': EsCleanupCompensation, 'api_recovery': ApiResourceRecoveryEvidence,
                 'checkpoints': EsCleanupCheckpoint, 'results': EsCleanupCheckResult}[info.field_name]
        def parse(item):
            return model.model_validate(item.model_dump() if isinstance(item, BaseModel) else item).model_dump(mode='json')
        if value is None:
            return None
        return [parse(item) for item in value] if info.field_name in ('checkpoints', 'results') else parse(value)


class CleanupHistoryEntry(StrictSchema):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    create_time: datetime
    operator_id: int | None = Field(default=None, ge=1)
    kind: str
    evidence: CleanupEventEvidence

    @field_validator('kind')
    @classmethod
    def validate_kind(cls, value):
        ResourceCleanupEventEnum(value)
        return value
