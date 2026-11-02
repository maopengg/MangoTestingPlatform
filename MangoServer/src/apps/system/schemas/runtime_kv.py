from datetime import datetime

from pydantic import Field, JsonValue

from src.common.schemas import StrictSchema


class RuntimeKVValueSchema(StrictSchema):
    data: JsonValue


class RuntimeKVWriteSchema(StrictSchema):
    key: str = Field(strict=True, min_length=1, max_length=192, pattern=r'^[!-~]+$')
    value: JsonValue
    ttl: int | None = Field(default=None, strict=True, ge=-2147483648, le=2147483647)


class RuntimeKVEntrySchema(StrictSchema):
    found: bool
    value: JsonValue = None
    value_type: int | None = None
    version: str | None = None
    expires_at: datetime | None = None
    ttl: int = -2
