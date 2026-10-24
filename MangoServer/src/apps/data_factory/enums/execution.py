from src.common.enums.base import BaseEnum


class DataFactoryExecutionSourceEnum(BaseEnum):
    """执行来源"""
    TEMPLATE_DEBUG = 1
    MANUAL = 2
    SYSTEM = 3
    API_CASE = 4
    API_CASE_PARAMETER = 5
    UI_CASE = 6

    @classmethod
    def obj(cls):
        return {1: "模板调试", 2: "手动执行", 3: "系统调用", 4: "API用例", 5: "API接口场景", 6: "UI用例"}


class DataFactoryCaseSourceTypeEnum(BaseEnum):
    """用例配置来源"""
    API_CASE = 1
    UI_CASE = 2
    API_CASE_PARAMETER = 3

    @classmethod
    def obj(cls):
        return {1: "API用例", 2: "UI用例", 3: "API接口场景"}


class DataFactoryExecutionStageEnum(BaseEnum):
    """执行阶段"""
    DEBUG = 1
    CREATE = 2
    CLEANUP = 3

    @classmethod
    def obj(cls):
        return {1: "调试", 2: "创建", 3: "清理"}


class DataFactoryExecutionStatusEnum(BaseEnum):
    """执行状态"""
    FAIL = 0
    SUCCESS = 1
    PENDING = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}
