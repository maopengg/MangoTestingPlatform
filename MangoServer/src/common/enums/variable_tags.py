from src.common.enums.base import BaseEnum


class VariableTagOperationEnum(BaseEnum):
    ADD = 0
    REMOVE = 1
    REPLACE = 2

    @classmethod
    def obj(cls):
        return {0: '添加标签', 1: '移除标签', 2: '替换标签'}
