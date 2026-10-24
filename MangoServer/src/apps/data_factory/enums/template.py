from src.common.enums.base import BaseEnum


class DataFactoryTemplateConfigStatusEnum(BaseEnum):
    """状态模板配置状态"""
    INCOMPLETE = 0
    READY = 1

    @classmethod
    def obj(cls):
        return {0: "待完善", 1: "已就绪"}


class DataFactoryTemplateUsageScopeEnum(BaseEnum):
    """场景模板用途"""
    CASE = 1
    INTERNAL = 2

    @classmethod
    def obj(cls):
        return {1: "用例可直接选择", 2: "仅场景内部引用"}
