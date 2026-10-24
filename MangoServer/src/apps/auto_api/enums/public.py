from src.common.enums.base import BaseEnum


class ApiPublicTypeEnum(BaseEnum):
    """全局变量类型"""
    CUSTOM = 0
    SQL = 1
    CODE = 2

    @classmethod
    def obj(cls):
        return {0: "自定义-第一加载", 1: "SQL-第二加载", 2: "代码变量-第三加载"}
