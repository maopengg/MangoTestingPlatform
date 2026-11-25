from datetime import date
from typing import Literal

from pydantic import Field, field_validator
from django.utils import timezone
from django.conf import settings

from src.common.schemas import StrictSchema, TrimmedStrictSchema
from src.apps.test_center.enums.environment import EnvironmentEnum


class ContentSearchQuery(TrimmedStrictSchema):
    project_product_id: int | None = Field(default=None, gt=0, strict=True)
    test_env: int | None = Field(default=None, strict=True)
    day: date
    keyword: str = Field(min_length=1, max_length=200)

    @field_validator('test_env')
    @classmethod
    def valid_environment(cls, value):
        if value is not None and value not in EnvironmentEnum.default_obj():
            raise ValueError('请选择有效的被测环境')
        return value

    @field_validator('day')
    @classmethod
    def recent_day(cls, value, info):
        if info.context and info.context.get('persisted'):
            return value
        today = timezone.localdate() if settings.USE_TZ else timezone.now().date()
        if not 0 <= (today - value).days < 30:
            raise ValueError('请选择最近30天内的单个日期')
        return value


class ContentSearchHit(StrictSchema):
    record_id: int
    target_type: str
    target_id: int | None = None
    name: str = ''
    create_time: str
    source_type: str = ''
    stage: str = ''
    report_id: int | None = None
    trigger_user: str = ''
    path: str
    snippet: str


class ContentSearchTask(StrictSchema):
    version: Literal[2] = 2
    task_id: str
    owner_id: int
    kind: str
    query: ContentSearchQuery
    product_scope: list[int] | None = None
    status: str = 'running'
    started_at: float
    updated_at: float
    scanned: int = 0
    skipped: int = 0
    read_bytes: int = 0
    match_count: int = 0
    message: str = ''
    items: list[ContentSearchHit] = Field(default_factory=list, max_length=20)
