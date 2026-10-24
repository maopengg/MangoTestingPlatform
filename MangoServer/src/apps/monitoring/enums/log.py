from src.common.enums.base import BaseEnum


class MonitoringLogStatusEnum(BaseEnum):
    """预警监控报告状态枚举"""
    INFO = 0
    ERROR = 1
    WARNING = 2
    DEBUG = 3

    @classmethod
    def obj(cls):
        return {
            0: '信息',
            1: '失败',
            2: '警告',
            3: '调试',
        }
