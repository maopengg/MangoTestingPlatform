import re
from pydantic import Field, JsonValue, model_validator
from src.common.schemas.base import StrictSchema
from src.apps.evaluation.enums.data_source import EvaluationItemSourceEnum
from .workflow import EvaluationWorkflowBinding, EvaluationInputVariable


class EvaluationItemDataSource(StrictSchema):
    kind: EvaluationItemSourceEnum = EvaluationItemSourceEnum.MANUAL
    binding: EvaluationWorkflowBinding | None = None
    query: str = Field(default="", max_length=100000)
    key: str = Field(default="", max_length=1000)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    module_id: int | None = Field(default=None, gt=0)
    variables: list[EvaluationInputVariable] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_source(self):
        if self.kind == EvaluationItemSourceEnum.API:
            names = [variable.name for variable in self.variables]
            if not names:
                raise ValueError("请配置参考接口响应的提取变量")
            if any(variable.path != variable.path.strip() for variable in self.variables):
                raise ValueError("响应 JSONPath 不能包含首尾空白")
            if len(set(names)) != len(names) or set(names) & {"steps", "session", "execution", "turn"}:
                raise ValueError("提取变量不能重复或使用 steps、session、execution、turn 保留名称")
        elif self.variables or self.module_id is not None:
            raise ValueError("接口模块和响应变量仅适用于参考接口查询")
        if self.kind != EvaluationItemSourceEnum.MANUAL and self.binding is None:
            raise ValueError("请选择条目的数据来源资源")
        if self.kind == EvaluationItemSourceEnum.SQL and not self.query.strip():
            raise ValueError("请填写该条目的 SQL 查询")
        self.key = self.key.strip()
        if self.key:
            keys = [part.strip() for part in self.key.split(',') if part.strip()]
            if self.kind != EvaluationItemSourceEnum.SQL:
                raise ValueError("变量 Key 仅适用于 SQL 查询")
            if not keys or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", key) for key in keys):
                raise ValueError("变量 Key 需为字母或下划线开头的名称，多个名称用英文逗号分隔")
            if len(keys) != len(set(keys)) or set(keys) & {"steps", "session", "execution", "turn"}:
                raise ValueError("变量 Key 不能重复或使用 steps、session、execution、turn 保留名称")
            self.key = ','.join(keys)
        if self.kind == EvaluationItemSourceEnum.MANUAL and (self.binding or self.query or self.parameters):
            raise ValueError("手动填写的条目不能保留动态数据来源")
        return self
