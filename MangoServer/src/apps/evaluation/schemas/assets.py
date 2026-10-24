import re
from typing import Annotated
from pydantic import Field, field_validator
from src.common.schemas.base import TrimmedStrictSchema
from src.apps.evaluation.schemas.case import EvaluationCaseConfig


class EvaluationCaseAssetCreate(TrimmedStrictSchema):
    name: str = Field(min_length=1, max_length=128)
    dataset_version_id: int | None = Field(default=None, gt=0)
    project_product_id: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=10000)
    config: EvaluationCaseConfig | None = None


class EvaluationDatasetTaskTypes(TrimmedStrictSchema):
    task_type: list[Annotated[str, Field(strict=True, min_length=1, max_length=64)]] = Field(min_length=1, max_length=50)

    @field_validator("task_type", mode="before")
    @classmethod
    def normalize_task_types(cls, value):
        if not isinstance(value, list):
            return value
        normalized = []
        for entry in value:
            if not isinstance(entry, str):
                normalized.append(entry)
                continue
            for tag in re.split(r"[,，\n]", entry):
                tag = tag.strip()
                if tag and tag not in normalized:
                    normalized.append(tag)
        return normalized


class EvaluationDatasetAssetCreate(EvaluationDatasetTaskTypes):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=10000)
