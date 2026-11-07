from typing import Literal

from pydantic import Field, field_validator

from src.apps.test_center.enums.environment import EnvironmentEnum
from src.common.schemas import StrictSchema


class MonitoringTaskPatch(StrictSchema):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    script_content: str | None = Field(default=None, min_length=1, max_length=1024 * 1024)
    test_env: int | None = None
    is_notice: Literal[0, 1] | None = None
    notice_group_id: int | None = Field(default=None, gt=0)

    @field_validator('name', 'script_content')
    @classmethod
    def reject_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('字段内容不能为空')
        return value

    @field_validator('test_env')
    @classmethod
    def valid_environment(cls, value):
        if value is not None and value not in EnvironmentEnum.obj():
            raise ValueError('被测环境无效')
        return value


class MonitoringTaskCreate(MonitoringTaskPatch):
    name: str = Field(min_length=1, max_length=128)
    script_content: str = Field(min_length=1, max_length=1024 * 1024)
    is_notice: Literal[0, 1] = 0
