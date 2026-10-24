from src.common.enums.base import BaseEnum


class PerfRunNodeStatusEnum(BaseEnum):
    CREATED = ("created", "已创建")
    RESERVED = ("reserved", "已预留")
    DISPATCHED = ("dispatched", "已下发")
    CLAIMED = ("claimed", "已领取")
    READY = ("ready", "已就绪")
    RUNNING = ("running", "运行中")
    LOST = ("lost", "已失联")
    SUCCESS = ("success", "成功")
    FAILED = ("failed", "失败")
    STOPPED = ("stopped", "已停止")
    CANCELLED = ("cancelled", "已取消")
    TIMEOUT = ("timeout", "已超时")

    @classmethod
    def terminal_values(cls) -> set[str]:
        return {cls.SUCCESS.value, cls.FAILED.value, cls.STOPPED.value, cls.CANCELLED.value, cls.TIMEOUT.value}


class PerfReservationStatusEnum(BaseEnum):
    RESERVED = ("reserved", "已预留")
    CLAIMED = ("claimed", "已领取")
    RELEASED = ("released", "已释放")
    EXPIRED = ("expired", "已过期")


class PerfRunNodeErrorCodeEnum(BaseEnum):
    EXECUTOR_HEARTBEAT_TIMEOUT = "executor_heartbeat_timeout"
