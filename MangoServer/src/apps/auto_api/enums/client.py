from src.common.enums.base import BaseEnum


class ApiClientEnum(BaseEnum):
    """设备类型"""
    WEB = 0, "WEB"
    PC = 1, "PC桌面"
    APP = 2, "APP"
    MINI = 3, "小程序"
