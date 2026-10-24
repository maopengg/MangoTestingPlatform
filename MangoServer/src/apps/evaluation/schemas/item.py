from decimal import Decimal
from typing import Literal
from pydantic import Field, JsonValue
from src.common.schemas.base import StrictSchema
from .case import EvaluationItemGrading
from .workflow import EvaluationItemScenario
from .data_source import EvaluationItemDataSource


class EvaluationDatasetItemPayload(StrictSchema):
    input_data: JsonValue = Field(default_factory=dict)
    expected_output: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    priority: Literal["P0", "P1", "P2", "P3"] = "P1"
    weight: Decimal = Field(default=Decimal("1"), gt=0, max_digits=8, decimal_places=3, allow_inf_nan=False)
    enabled: bool = True
    grading_config: EvaluationItemGrading = Field(default_factory=EvaluationItemGrading)
    scenario: EvaluationItemScenario = Field(default_factory=EvaluationItemScenario)
    data_source: EvaluationItemDataSource = Field(default_factory=EvaluationItemDataSource)
