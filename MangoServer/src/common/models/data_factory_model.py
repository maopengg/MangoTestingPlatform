# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂数据模型

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator


SUPPORTED_GENERATOR_TYPES = {0, 1, 2, 3, 4, 5, 6, 7, 9, 11, 13}


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataFactoryEmptyGeneratorConfig(_StrictConfigModel):
    """不需要配置的生成方式"""


class DataFactorySkipGeneratorConfig(_StrictConfigModel):
    """跳过字段生成配置"""
    reason: str | None = None


class DataFactoryFixedGeneratorConfig(_StrictConfigModel):
    """固定值生成配置"""
    value: Any = None


class DataFactoryRandomStringGeneratorConfig(_StrictConfigModel):
    """随机字符串生成配置"""
    prefix: str = ""
    length: int = 8

    @field_validator("length")
    @classmethod
    def validate_length(cls, value: int):
        if value <= 0:
            raise ValueError("length 必须大于 0")
        return value


class DataFactoryRandomNumberGeneratorConfig(_StrictConfigModel):
    """随机整数/小数生成配置"""
    min: int | float = 1
    max: int | float = 100

    @model_validator(mode="after")
    def validate_range(self):
        if self.min > self.max:
            raise ValueError("min 不能大于 max")
        return self


class DataFactoryRandomDecimalGeneratorConfig(DataFactoryRandomNumberGeneratorConfig):
    """随机小数生成配置"""
    precision: int = 2

    @field_validator("precision")
    @classmethod
    def validate_precision(cls, value: int):
        if value < 0:
            raise ValueError("precision 不能小于 0")
        return value


class DataFactoryRelativeTimeGeneratorConfig(_StrictConfigModel):
    """相对时间生成配置"""
    days: int = 0
    hours: int = 0
    minutes: int = 0


class DataFactoryUuidGeneratorConfig(_StrictConfigModel):
    """UUID 生成配置"""
    dash: bool = False


class DataFactoryEnumOption(BaseModel):
    """枚举展示选项"""
    model_config = ConfigDict(extra="allow")

    label: str | int | float | bool | None = None
    value: Any = None


class DataFactoryEnumGeneratorConfig(_StrictConfigModel):
    """枚举生成配置"""
    values: list[Any] = Field(default_factory=list)
    options: list[DataFactoryEnumOption] = Field(default_factory=list)
    mode: Literal["fixed", "random"] = "fixed"
    value: Any = None

    @model_validator(mode="after")
    def validate_fixed_value(self):
        if self.mode == "fixed" and self.values and self.value is not None and self.value not in self.values:
            raise ValueError("枚举固定值必须在 values 范围内")
        return self


class DataFactoryEntityDependencyGeneratorConfig(_StrictConfigModel):
    """工厂实体字段规则中的依赖实体字段配置"""
    dependency_entity_id: int
    field: str = "id"


class DataFactoryOverrideDependencyGeneratorConfig(DataFactoryEntityDependencyGeneratorConfig):
    """状态模板/API 覆盖中的依赖实体字段配置"""
    template_id: int | None = None
    strategy: Literal["reuse_or_create", "must_exist", "create_always"] = "reuse_or_create"


class DataFactoryFunctionGeneratorConfig(_StrictConfigModel):
    """测试数据方法生成配置"""
    value: str

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str):
        if not value:
            raise ValueError("测试数据方法必须配置 value")
        return value


def _dump_config(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(exclude_none=True)


def validate_data_factory_generator_config(
        generator_type: int,
        generator_config: dict[str, Any] | None,
        *,
        allow_dependency_template: bool = False,
) -> dict[str, Any]:
    """按生成方式校验并清洗 generator_config。

    allow_dependency_template=False 用于工厂实体字段规则，依赖字段只允许 dependency_entity_id + field。
    allow_dependency_template=True 用于状态模板/API 覆盖，依赖字段允许额外 template_id + strategy。
    """
    config = generator_config or {}
    if not isinstance(config, dict):
        raise ValueError("generator_config 必须是对象")
    if generator_type not in SUPPORTED_GENERATOR_TYPES:
        raise ValueError("不支持的生成方式")

    if generator_type == 0:
        return _dump_config(DataFactorySkipGeneratorConfig.model_validate(config))
    if generator_type == 5:
        return _dump_config(DataFactoryEmptyGeneratorConfig.model_validate(config))
    if generator_type == 1:
        return _dump_config(DataFactoryFixedGeneratorConfig.model_validate(config))
    if generator_type == 2:
        return _dump_config(DataFactoryRandomStringGeneratorConfig.model_validate(config))
    if generator_type == 3:
        return _dump_config(DataFactoryRandomNumberGeneratorConfig.model_validate(config))
    if generator_type == 4:
        return _dump_config(DataFactoryRandomDecimalGeneratorConfig.model_validate(config))
    if generator_type == 6:
        return _dump_config(DataFactoryRelativeTimeGeneratorConfig.model_validate(config))
    if generator_type == 7:
        return _dump_config(DataFactoryUuidGeneratorConfig.model_validate(config))
    if generator_type == 9:
        return _dump_config(DataFactoryEnumGeneratorConfig.model_validate(config))
    if generator_type == 11:
        model = (
            DataFactoryOverrideDependencyGeneratorConfig
            if allow_dependency_template
            else DataFactoryEntityDependencyGeneratorConfig
        )
        return _dump_config(model.model_validate(config))
    if generator_type == 13:
        return _dump_config(DataFactoryFunctionGeneratorConfig.model_validate(config))
    return config


class DataFactoryFieldOverrideRule(BaseModel):
    """状态模板字段覆盖规则"""
    model_config = ConfigDict(extra="forbid")

    generator_type: int
    generator_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generator_type")
    @classmethod
    def validate_generator_type(cls, value: int):
        if value not in SUPPORTED_GENERATOR_TYPES:
            raise ValueError("不支持的生成方式")
        return value

    @model_validator(mode="after")
    def validate_generator_config(self):
        self.generator_config = validate_data_factory_generator_config(
            self.generator_type,
            self.generator_config,
            allow_dependency_template=True,
        )
        return self


class DataFactoryFieldOverrideRules(RootModel[dict[str, DataFactoryFieldOverrideRule]]):
    """状态模板字段覆盖规则集合"""
    root: dict[str, DataFactoryFieldOverrideRule] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, DataFactoryFieldOverrideRule]:
        return self.root


class DataFactoryOutputConfigItem(BaseModel):
    """状态模板输出配置"""
    model_config = ConfigDict(extra="forbid")

    field: str
    key: str

    @field_validator("field", "key")
    @classmethod
    def validate_required_text(cls, value: str):
        if not value:
            raise ValueError("不能为空")
        return value


class DataFactoryOutputConfig(RootModel[list[DataFactoryOutputConfigItem]]):
    """状态模板输出配置集合"""
    root: list[DataFactoryOutputConfigItem] = Field(default_factory=list)

    def to_list(self) -> list[DataFactoryOutputConfigItem]:
        return self.root


SCENE_MAIN_OVERRIDES_KEY = "__main__"
SCENE_ITEM_OVERRIDES_KEY = "__items__"


def validate_data_factory_scene_overrides(value: dict[str, Any] | None) -> dict[str, Any]:
    """校验场景模板/API 覆盖。

    兼容旧格式：普通字段覆盖字典仍表示主模板覆盖。
    新格式：{"__main__": {...}, "__items__": {"itemId/name": {...}}}。
    """
    data = value or {}
    if not isinstance(data, dict):
        raise ValueError("字段覆盖规则必须是对象")
    if SCENE_MAIN_OVERRIDES_KEY not in data and SCENE_ITEM_OVERRIDES_KEY not in data:
        return DataFactoryFieldOverrideRules.model_validate(data).model_dump()

    main_overrides = data.get(SCENE_MAIN_OVERRIDES_KEY) or {}
    item_overrides = data.get(SCENE_ITEM_OVERRIDES_KEY) or {}
    if not isinstance(item_overrides, dict):
        raise ValueError("__items__ 必须是对象")

    return {
        SCENE_MAIN_OVERRIDES_KEY: DataFactoryFieldOverrideRules.model_validate(main_overrides).model_dump(),
        SCENE_ITEM_OVERRIDES_KEY: {
            str(key): DataFactoryFieldOverrideRules.model_validate(item or {}).model_dump()
            for key, item in item_overrides.items()
        },
    }
