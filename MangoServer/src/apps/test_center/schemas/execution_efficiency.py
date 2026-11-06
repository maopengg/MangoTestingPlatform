from datetime import datetime, timedelta
from typing import Annotated, Literal

from django.utils import timezone
from django.conf import settings
from mangotools.enums import TestCaseTypeEnum
from pydantic import ConfigDict, Field, model_validator

from src.common.schemas import StrictSchema
from src.apps.test_center.exceptions import TestCenterError, EXECUTION_EFFICIENCY_RANGE_INVALID


class ExecutionEfficiencyQuery(StrictSchema):
    model_config = ConfigDict(extra='forbid', use_enum_values=True)
    section: Literal['queue', 'timing', 'anomalies'] = 'queue'
    start_at: datetime = Field(default_factory=lambda: timezone.now() - timedelta(hours=24))
    end_at: datetime = Field(default_factory=timezone.now)
    project_id: int | None = Field(default=None, gt=0)
    project_product_id: int | None = Field(default=None, gt=0)
    module_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=1000)
    test_env: list[int] = Field(default_factory=list, max_length=30)
    case_type: list[TestCaseTypeEnum] = Field(default_factory=list, max_length=10)
    task_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=100)
    task_group_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=100)
    report_id: int | None = Field(default=None, gt=0)
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode='after')
    def validate_range(self):
        for field in ('start_at', 'end_at'):
            value = getattr(self, field)
            if settings.USE_TZ and timezone.is_naive(value):
                value = timezone.make_aware(value)
            elif not settings.USE_TZ and timezone.is_aware(value):
                value = timezone.make_naive(value)
            setattr(self, field, value)
        if self.start_at >= self.end_at or self.end_at - self.start_at > timedelta(days=31):
            raise TestCenterError(EXECUTION_EFFICIENCY_RANGE_INVALID)
        return self
