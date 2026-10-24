from src.common.enums.base import BaseEnum


class MemoryFactStatusEnum(BaseEnum):
    SUPPORTED = ("supported", "完整支持")
    PARTIAL = ("partial", "部分支持")
    OMITTED = ("omitted", "遗漏")
    CONTRADICTED = ("contradicted", "矛盾")
    UNSUPPORTED = ("unsupported", "无依据")
    UNVERIFIABLE = ("unverifiable", "无法核对")
    ABSTAINED = ("abstained", "未作答或拒答")
    UNCHANGED = ("unchanged", "旧记忆未更新")
