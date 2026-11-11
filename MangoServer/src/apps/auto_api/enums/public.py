from src.common.enums.base import BaseEnum


class ApiPublicTypeEnum(BaseEnum):
    """全局变量类型"""
    CUSTOM = 0
    SQL = 1
    CODE = 2

    @classmethod
    def obj(cls):
        return {0: "① 自定义", 1: "② SQL", 2: "③ 代码变量"}
