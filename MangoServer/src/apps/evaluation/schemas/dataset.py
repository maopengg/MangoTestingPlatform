from typing import Literal
from pydantic import Field, model_validator
from src.common.schemas.base import StrictSchema
from .workflow import EvaluationInputVariable, EvaluationDatasetWorkflow


class EvaluationDatasetSchema(StrictSchema):
    schema_version: Literal[1] = 1
    hash_version: Literal[1] = 1
    input_schema: dict = Field(default_factory=dict)
    expected_schema: dict = Field(default_factory=dict)
    context_schema: dict = Field(default_factory=dict)
    metadata_schema: dict = Field(default_factory=dict)
    input_variables: list[EvaluationInputVariable] = Field(default_factory=lambda: [EvaluationInputVariable()], min_length=1, max_length=50)
    workflow: EvaluationDatasetWorkflow = Field(default_factory=EvaluationDatasetWorkflow)

    @model_validator(mode="after")
    def unique_variables(self):
        names = [variable.name for variable in self.input_variables]
        if len(set(names)) != len(names) or any(name in {"steps", "session", "execution", "turn"} for name in names):
            raise ValueError("输入变量不能重复或使用 steps、session、execution、turn 保留名称")
        return self
