from src.common.enums.base import BaseEnum


class GrayCaseTypeEnum(BaseEnum):
    API = 1
    UI = 2

    @classmethod
    def obj(cls):
        return {cls.API.value: "API用例", cls.UI.value: "UI用例"}


class GrayCaseScopeEnum(BaseEnum):
    CASE = "case"
    API_STEP = "api_step"
    API_PARAMETER = "api_parameter"

    @classmethod
    def obj(cls):
        return {
            cls.CASE.value: "用例级",
            cls.API_STEP.value: "API步骤级",
            cls.API_PARAMETER.value: "API参数场景级",
        }
