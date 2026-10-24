from src.common.enums.base import BaseEnum


class PerfThresholdSeverityEnum(BaseEnum):
    WARNING = ("warning", "警告")
    CRITICAL = ("critical", "严重")


class PerfValidityStatusEnum(BaseEnum):
    PASSED = ("passed", "通过")
    FAILED = ("failed", "失败")
    NOT_APPLICABLE = ("not_applicable", "不适用")
