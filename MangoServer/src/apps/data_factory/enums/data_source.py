from src.common.enums.base import BaseEnum


class DataFactorySourceModeEnum(BaseEnum):
    """数据库模式"""
    FIXED_DATABASE = 1
    FOLLOW_ENVIRONMENT = 2

    @classmethod
    def obj(cls):
        return {1: "固定数据库", 2: "跟随执行环境"}


class DataFactoryOperationTypeEnum(BaseEnum):
    """创建/删除方式"""
    API = 1
    SQL = 2
    FUNCTION = 3

    @classmethod
    def obj(cls):
        return {1: "API", 2: "SQL", 3: "自定义函数"}


class DataFactoryErrorCodeEnum(BaseEnum):
    TEST_OBJECT_NOT_FOUND = "TEST_OBJECT_NOT_FOUND"
