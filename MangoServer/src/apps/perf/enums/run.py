from src.common.enums.base import BaseEnum


class PerfRunStatusEnum(BaseEnum):
    CREATED = ("created", "已创建")
    PRECHECKING = ("prechecking", "预检中")
    WAITING_EXECUTOR = ("waiting_executor", "等待执行器")
    QUEUED = ("queued", "排队中")
    STARTING = ("starting", "启动中")
    RUNNING = ("running", "运行中")
    STOPPING = ("stopping", "停止中")
    AGGREGATING = ("aggregating", "汇总中")
    COMPLETED = ("completed", "已完成")
    PARTIAL = ("partial", "部分完成")
    FAILED = ("failed", "执行失败")
    STOPPED = ("stopped", "已停止")
    CANCELLED = ("cancelled", "已取消")
    TIMEOUT = ("timeout", "已超时")

    @classmethod
    def terminal_values(cls) -> set[str]:
        return {cls.COMPLETED.value, cls.PARTIAL.value, cls.FAILED.value, cls.STOPPED.value,
                cls.CANCELLED.value, cls.TIMEOUT.value}


class PerfRunVerdictEnum(BaseEnum):
    NOT_EVALUATED = ("not_evaluated", "未判定")
    PASSED = ("passed", "通过")
    FAILED = ("failed", "不通过")
    INVALID = ("invalid", "结果无效")
