from typing import Annotated
from pydantic import Field, JsonValue, model_validator
from src.common.schemas.base import StrictSchema
from src.apps.evaluation.enums.execution import EvaluationExecutionStatusEnum, EvaluationVerdictEnum
from src.apps.evaluation.enums.workflow import (
    EvaluationPreparationEnum, EvaluationSequenceEnum, EvaluationWorkflowActionEnum,
    EvaluationWorkflowStageEnum, EvaluationWorkflowScopeEnum,
    EvaluationTurnKindEnum,
)


class EvaluationInputVariable(StrictSchema):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$", default="case_input")
    path: str = Field(default="$", min_length=1, max_length=512, pattern=r"^\$")


class EvaluationWorkflowStep(StrictSchema):
    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=128)
    stage: EvaluationWorkflowStageEnum = EvaluationWorkflowStageEnum.PREPARE
    scope: EvaluationWorkflowScopeEnum = EvaluationWorkflowScopeEnum.ITEM
    action: EvaluationWorkflowActionEnum = EvaluationWorkflowActionEnum.API
    resource: str = Field(default="", max_length=64)
    code: str = Field(default="", max_length=100000)
    input_data: JsonValue = Field(default_factory=dict)
    paths: list[Annotated[str, Field(pattern=r"^\$", max_length=512)]] = Field(default_factory=list, max_length=20)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    until_path: str = Field(default="", max_length=512)
    until_value: JsonValue = True
    failure_path: str = Field(default="", max_length=512)
    failure_value: JsonValue = True
    interval_seconds: float = Field(default=1, ge=0.1, le=60)
    turn_kind: EvaluationTurnKindEnum | None = None
    iterate_path: str = Field(default="", max_length=512)

    @model_validator(mode="after")
    def validate_step(self):
        if self.action == EvaluationWorkflowActionEnum.SCRIPT and not self.code.strip():
            raise ValueError("请填写流程 Python 脚本")
        if self.action != EvaluationWorkflowActionEnum.SCRIPT and not self.resource:
            raise ValueError("请选择流程资源")
        if self.stage == EvaluationWorkflowStageEnum.READY and not self.until_path:
            raise ValueError("就绪检查需要配置成功条件")
        if self.stage in {EvaluationWorkflowStageEnum.BEFORE_TURN, EvaluationWorkflowStageEnum.AFTER_TURN, EvaluationWorkflowStageEnum.REFERENCE} and self.scope != EvaluationWorkflowScopeEnum.ITEM:
            raise ValueError("轮次与标准答案步骤必须按每条数据执行")
        if any(path and not path.startswith("$") for path in (self.until_path, self.failure_path)):
            raise ValueError("检查条件必须使用 JSONPath")
        if self.iterate_path and (not self.iterate_path.startswith("$") or self.stage == EvaluationWorkflowStageEnum.REFERENCE):
            raise ValueError("列表路径必须使用 JSONPath，标准答案步骤不支持列表循环")
        if self.action == EvaluationWorkflowActionEnum.FACTORY and self.until_path:
            raise ValueError("数据工厂不能作为重复调用的等待步骤")
        return self


class EvaluationWorkflowBinding(StrictSchema):
    name: str = Field(default="", max_length=256)
    resource: str = Field(min_length=1, max_length=64)
    project_product_id: int = Field(gt=0)
    ref_id: int = Field(gt=0)
    revision_id: int | None = Field(default=None, gt=0)
    content_hash: str = ""
    target_ref_id: int | None = Field(default=None, gt=0)


class EvaluationDatasetWorkflow(StrictSchema):
    preparation: EvaluationPreparationEnum = EvaluationPreparationEnum.NONE
    sequence: EvaluationSequenceEnum = EvaluationSequenceEnum.INDEPENDENT
    steps: list[EvaluationWorkflowStep] = Field(default_factory=list, max_length=100)
    bindings: list[EvaluationWorkflowBinding] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def unique_resources(self):
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("流程步骤标识重复")
        identities = [(item.resource, item.project_product_id, item.target_ref_id) for item in self.bindings]
        if len(identities) != len(set(identities)):
            raise ValueError("同一项目产品的流程资源绑定不能重复")
        return self


class EvaluationScenarioTurn(StrictSchema):
    kind: EvaluationTurnKindEnum = EvaluationTurnKindEnum.TEST
    name: str = Field(default="", max_length=128)
    input_data: JsonValue = Field(default_factory=dict)
    expected_output: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    score: bool = True

    @model_validator(mode="after")
    def material_not_scored(self):
        if self.kind == EvaluationTurnKindEnum.MATERIAL and self.score:
            raise ValueError("写入材料不参与评分")
        return self


class EvaluationItemScenario(StrictSchema):
    group_key: str = Field(default="", max_length=128)
    order: int = Field(default=0, ge=0)
    turns: list[EvaluationScenarioTurn] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def require_scored_turn(self):
        if self.turns and not any(turn.score for turn in self.turns):
            raise ValueError("多轮条目至少需要一个参与评分的轮次")
        return self


class EvaluationWorkflowRecord(StrictSchema):
    step_id: str
    name: str
    stage: EvaluationWorkflowStageEnum
    scope: EvaluationWorkflowScopeEnum
    item_id: int | None = Field(default=None, gt=0)
    status: EvaluationExecutionStatusEnum
    output: JsonValue = None
    error_message: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)


class EvaluationTurnResult(StrictSchema):
    index: int = Field(ge=1)
    name: str
    input: JsonValue
    expected: dict
    output: JsonValue
    scored: bool
    score: float | None = Field(default=None, ge=0, le=100)
    verdict: EvaluationVerdictEnum
