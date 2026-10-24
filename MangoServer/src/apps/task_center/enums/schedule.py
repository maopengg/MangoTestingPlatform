from src.common.enums.base import BaseEnum


class ScheduleFireStatusEnum(BaseEnum):
    PENDING = 0
    DISPATCHING = 1
    DISPATCHED = 2
    SUCCESS = 3
    FAIL = 4
    SKIPPED = 5
    CANCELLED = 6

    @classmethod
    def obj(cls):
        return {
            0: "待分发",
            1: "分发中",
            2: "已分发",
            3: "成功",
            4: "失败",
            5: "已跳过",
            6: "已取消",
        }


class ScheduleFireSourceTypeEnum(BaseEnum):
    TEST_SUITE = 0
    TOKEN_REFRESH = 1
    DATA_CLEANUP = 2
    MONITORING = 3
    SYSTEM_JOB = 4

    @classmethod
    def obj(cls):
        return {
            0: "测试套执行",
            1: "Token刷新",
            2: "数据清理",
            3: "监控任务",
            4: "系统定时任务",
        }


class ScheduledTaskGroupSyncStatusEnum(BaseEnum):
    """模块任务组及成员的同步状态。"""
    PENDING = 'pending'
    SYNCED = 'synced'
    FAILED = 'failed'
    ARCHIVED = 'archived'

    @classmethod
    def obj(cls):
        return {
            cls.PENDING.value: '待同步',
            cls.SYNCED.value: '已同步',
            cls.FAILED.value: '同步失败',
            cls.ARCHIVED.value: '已归档',
        }
