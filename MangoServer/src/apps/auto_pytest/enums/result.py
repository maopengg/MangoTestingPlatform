from src.common.enums.base import BaseEnum


class AllureStatusEnum(BaseEnum):
    """方法枚举"""
    SUCCESS = 'passed'
    FAIL = 'failed'
    BROKEN = 'broken'

    @classmethod
    def obj(cls):
        return {0: "未绑定", 1: "已绑定", 2: "已删除"}


class PytestSystemEnum(BaseEnum):
    TEST_ENV = 'MANGO_TEST_ENV'
