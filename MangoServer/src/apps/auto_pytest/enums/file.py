from src.common.enums.base import BaseEnum


class FileStatusEnum(BaseEnum):
    """平台模块绑定状态。"""
    UNBOUND = 0
    ALREADY_BOUND = 1

    @classmethod
    def obj(cls):
        return {0: "未绑定", 1: "已绑定"}
