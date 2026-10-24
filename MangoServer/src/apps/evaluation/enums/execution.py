from src.common.enums.base import BaseEnum


class EvaluationCaseExecutionStatusEnum(BaseEnum):
    PENDING = ("pending", "待执行")
    PREPARING = ("preparing", "准备中")
    RUNNING = ("running", "执行中")
    AGGREGATING = ("aggregating", "汇总中")
    COMPLETED = ("completed", "已完成")
    FAILED = ("failed", "执行失败")
    STOPPING = ("stopping", "停止中")
    STOPPED = ("stopped", "已停止")

    @classmethod
    def terminal_values(cls):
        return {cls.COMPLETED.value, cls.FAILED.value, cls.STOPPED.value}


class EvaluationExecutionStatusEnum(BaseEnum):
    PENDING = ("pending", "待执行")
    RUNNING = ("running", "执行中")
    SUCCESS = ("success", "成功")
    FAILED = ("failed", "失败")
    TIMEOUT = ("timeout", "超时")
    CANCELLED = ("cancelled", "已取消")


class EvaluationGradeStatusEnum(BaseEnum):
    PENDING = ("pending", "待评测")
    GRADING = ("grading", "评测中")
    GRADED = ("graded", "已评测")
    INVALID = ("invalid", "无效")
    FAILED = ("failed", "评测失败")


class EvaluationVerdictEnum(BaseEnum):
    NOT_EVALUATED = ("not_evaluated", "未判定")
    PASSED = ("passed", "通过")
    FAILED = ("failed", "不通过")
    WARNING = ("warning", "警告")
    INVALID = ("invalid", "结果无效")


class EvaluationTriggerTypeEnum(BaseEnum):
    MANUAL = ("manual", "手动")
    API = ("api", "API")
    RETRY = ("retry", "重试")
