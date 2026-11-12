from typing import Literal

from pydantic import Field, JsonValue, StrictBool, StrictInt, model_validator
from typing_extensions import Self

from src.common.schemas import StrictSchema


class InterfaceActionBarPreferences(StrictSchema):
    isShowSearch: StrictBool = True
    isShowMessage: StrictBool = True
    isShowRefresh: StrictBool = True
    isShowFullScreen: StrictBool = True


class InterfacePreferences(StrictSchema):
    themePreset: Literal[
        'mango-blue', 'tech-cyan', 'graphite-dark', 'dopamine-pop',
        'royal-purple', 'morandi', 'slate-indigo', 'forest-console', 'ocean-graphite',
    ] = 'mango-blue'
    sideTheme: Literal['dark', 'white', 'blue', 'image'] = 'white'
    layoutMode: Literal['ltr', 'lcr', 'ttb'] = 'ltr'
    displayDensity: Literal['auto', 'compact', 'standard', 'comfortable'] = 'auto'
    autoScale2k: float = Field(default=1.15, ge=1, le=3, strict=True, allow_inf_nan=False)
    autoScale4k: float = Field(default=1.35, ge=1, le=3, strict=True, allow_inf_nan=False)
    sideWidth: StrictInt = Field(default=200, ge=168, le=280)
    pageAnim: Literal['fade', 'opacity', 'down', 'scale'] = 'opacity'
    isFixedNavBar: StrictBool = True
    actionBar: InterfaceActionBarPreferences = Field(default_factory=InterfaceActionBarPreferences)

    @model_validator(mode='after')
    def validate_scale_order(self) -> Self:
        if self.autoScale4k < self.autoScale2k:
            raise ValueError('autoScale4k must be greater than or equal to autoScale2k')
        return self


class UserConfigItemUpdate(StrictSchema):
    key: str = Field(min_length=1, max_length=128)
    value: JsonValue


class UserConfigBatch(StrictSchema):
    items: list[UserConfigItemUpdate] = Field(min_length=1, max_length=100)
