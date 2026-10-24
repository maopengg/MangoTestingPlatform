from typing import Literal
from pydantic import Field, model_validator
from src.apps.evaluation.enums import EvaluationTargetTypeEnum
from src.common.schemas.base import StrictSchema


class EvaluationTargetVersion(StrictSchema):
    kind: Literal["api_info_revision", "api_info_release"]
    id: int = Field(gt=0, le=9223372036854775807)


class EvaluationTargetConfig(StrictSchema):
    code: str = Field(default="", max_length=100000)


class EvaluationTargetBinding(StrictSchema):
    type: EvaluationTargetTypeEnum
    ref_id: int | None = Field(default=None, gt=0, le=9223372036854775807)
    version_ref: EvaluationTargetVersion | None = None
    parameters: EvaluationTargetConfig = Field(default_factory=EvaluationTargetConfig)

    @model_validator(mode="after")
    def validate_version(self):
        kind = self.type.value
        if kind not in ("api_info", "script"):
            raise ValueError("当前仅支持接口管理和 Python 脚本")
        if kind == "script":
            if self.ref_id is not None or self.version_ref is not None:
                raise ValueError("Python 脚本不接受接口或版本引用")
        elif kind == "api_info" and self.ref_id is None and self.version_ref is None:
            pass
        else:
            if self.ref_id is None or self.version_ref is None or not self.version_ref.kind.startswith(kind + "_"):
                raise ValueError("目标必须绑定所属类型的固定版本")
        if kind == "api_info" and self.parameters.code:
            raise ValueError("接口目标不接受 Python 脚本")
        return self
