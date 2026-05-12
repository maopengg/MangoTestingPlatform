# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂数据模型

from typing import Any

from pydantic import BaseModel, Field, RootModel, field_validator


SUPPORTED_GENERATOR_TYPES = {0, 1, 2, 3, 4, 5, 6, 7, 9, 11, 13}


class DataFactoryFieldOverrideRule(BaseModel):
    """状态模板字段覆盖规则"""
    generator_type: int
    generator_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generator_type")
    @classmethod
    def validate_generator_type(cls, value: int):
        if value not in SUPPORTED_GENERATOR_TYPES:
            raise ValueError("不支持的生成方式")
        return value


class DataFactoryFieldOverrideRules(RootModel[dict[str, DataFactoryFieldOverrideRule]]):
    """状态模板字段覆盖规则集合"""
    root: dict[str, DataFactoryFieldOverrideRule] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, DataFactoryFieldOverrideRule]:
        return self.root


class DataFactoryOutputConfigItem(BaseModel):
    """状态模板输出配置"""
    field: str
    key: str


class DataFactoryOutputConfig(RootModel[list[DataFactoryOutputConfigItem]]):
    """状态模板输出配置集合"""
    root: list[DataFactoryOutputConfigItem] = Field(default_factory=list)

    def to_list(self) -> list[DataFactoryOutputConfigItem]:
        return self.root
