from src.common.enums.base import BaseEnum


class DataFactoryCleanupModeEnum(BaseEnum):
    SYNCHRONOUS = 'synchronous'
    SCHEDULED = 'scheduled'


class DataFactoryCleanupStrategyEnum(BaseEnum):
    """清理策略"""
    EXECUTION_END = 1
    MANUAL = 2
    NONE = 3

    @classmethod
    def obj(cls):
        return {1: "执行结束", 2: "手动清理", 3: "不清理"}


class DataFactoryCleanupStatusEnum(BaseEnum):
    """清理状态"""
    NOT_CLEANED = 0
    SUCCESS = 1
    FAIL = 2
    SKIPPED = 3
    PENDING_MANUAL = 4

    @classmethod
    def obj(cls):
        return {
            0: "未清理",
            1: "已清理",
            2: "清理失败",
            3: "跳过清理",
            4: "待手动清理",
        }
