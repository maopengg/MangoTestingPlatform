from src.common.enums.base import BaseEnum


class TaskEnum(BaseEnum):
    """状态枚举"""
    FAIL = 0
    SUCCESS = 1
    STAY_BEGIN = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}


class MonitoringTaskStatusEnum(BaseEnum):
    """监控任务状态枚举"""
    QUEUED = 0
    RUNNING = 1
    STOPPED = 2
    FAILED = 3
    COMPLETED = 4
    STARTING = 5

    @classmethod
    def obj(cls):
        return {
            0: '待执行',
            1: '运行中',
            2: '已停止',
            3: '失败',
            4: '已完成',
            5: '启动中',
        }
