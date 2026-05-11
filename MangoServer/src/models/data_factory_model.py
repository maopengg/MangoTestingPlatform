# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂数据模型

from typing import Any

from pydantic import BaseModel, Field, RootModel


class DataFactoryFieldOverrideRule(BaseModel):
    """状态模板字段覆盖规则"""
    generator_type: int
    generator_config: dict[str, Any] = Field(default_factory=dict)


class DataFactoryFieldOverrideRules(RootModel[dict[str, DataFactoryFieldOverrideRule]]):
    """状态模板字段覆盖规则集合"""
    root: dict[str, DataFactoryFieldOverrideRule] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, DataFactoryFieldOverrideRule]:
        return self.root
