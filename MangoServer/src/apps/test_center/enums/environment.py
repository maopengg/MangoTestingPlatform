from src.common.enums.base import BaseEnum


class AutoTypeEnum(BaseEnum):
    """说明这个测试环境给那个自动化使用"""
    CURRENCY = 0
    UI = 1
    API = 2
    EVALUATION = 3

    @classmethod
    def obj(cls):
        return {0: "UI/API通用", 1: "UI自动化", 2: "API自动化", 3: "效果测试"}


class EnvironmentEnum(BaseEnum):
    """测试环境枚举"""
    TEST = 0
    PRE = 1
    PRO = 2
    DEV = 3
    UAT = 4
    SIM = 5

    @classmethod
    def default_obj(cls):
        return {
            cls.DEV.value: "开发环境",
            cls.TEST.value: "测试环境",
            cls.PRE.value: "预发环境",
            cls.UAT.value: "验收环境",
            cls.SIM.value: "仿真环境",
            cls.PRO.value: "生产环境",
        }

    @classmethod
    def obj(cls):
        from src.apps.system.services.system_config import SystemConfigService

        aliases = SystemConfigService.get_environment_display_names()
        return {key: aliases.get(str(key), name) for key, name in cls.default_obj().items()}

    @classmethod
    def choices(cls):
        # Model choices stay static: importing models must not read configuration or change migration state.
        return sorted(cls.default_obj().items())
