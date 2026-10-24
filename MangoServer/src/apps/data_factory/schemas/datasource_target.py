from datetime import datetime

from pydantic import Field

from src.common.schemas import FrozenSchema, TrimmedStrictSchema


class DatasourceBindingTarget(TrimmedStrictSchema):
    database_name: str = Field(default='', max_length=128)
    schema_name: str = Field(default='', max_length=128)
    redis_db: int | None = Field(default=None, ge=0, strict=True)


class DatasourceTarget(FrozenSchema):
    id: int
    db_type: int
    source_category: int
    display_name: str
    host: str
    port: int
    user: str
    password: str = Field(repr=False, exclude=True)
    file_path: str = ''
    extra_config: dict
    update_time: datetime
    database_name: str = ''
    schema_name: str = ''
    redis_db: int | None = None
    cache_key: str
