from typing import Literal

from pydantic import Field

from src.common.schemas import TrimmedStrictSchema


class DataSourceAliasSuggestion(TrimmedStrictSchema):
    alias: str = Field(max_length=64)
    reason: str = Field(max_length=300)
    confidence: Literal['high', 'medium', 'low']
