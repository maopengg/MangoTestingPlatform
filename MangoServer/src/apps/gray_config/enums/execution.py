from src.common.enums.base import BaseEnum


class GrayExecutionStatusEnum(BaseEnum):
    WAITING = 0
    SUCCESS = 1
    FAILED = 2
    RESTORED = 3
    RESTORE_FAILED = 4

    @classmethod
    def obj(cls):
        return {
            cls.WAITING.value: "待执行",
            cls.SUCCESS.value: "成功",
            cls.FAILED.value: "失败",
            cls.RESTORED.value: "已恢复",
            cls.RESTORE_FAILED.value: "恢复失败",
        }


class GrayExecutionLockStatusEnum(BaseEnum):
    LOCKED = 1
    RELEASED = 2
    EXPIRED = 3

    @classmethod
    def obj(cls):
        return {
            cls.LOCKED.value: "锁定中",
            cls.RELEASED.value: "已释放",
            cls.EXPIRED.value: "已过期",
        }
