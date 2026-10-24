from src.common.enums.base import BaseEnum


class ManualTestSyncStatusEnum(BaseEnum):
    NOT_SYNCED = 0
    SYNCED = 1
    CHANGED = 2
    SYNC_FAILED = 3

    @classmethod
    def obj(cls):
        return {0: "未同步", 1: "已同步", 2: "有变更", 3: "同步失败"}


class ManualTestChangeStatusEnum(BaseEnum):
    UNCHANGED = 0
    ADDED = 1
    CHANGED = 2
    REMOVED = 3

    @classmethod
    def obj(cls):
        return {0: "无变化", 1: "新增", 2: "已变更", 3: "来源已移除"}


class ManualTestAutomationImpactStatusEnum(BaseEnum):
    NONE = 0
    PENDING_REVIEW = 1
    NEED_OPTIMIZE = 2
    OPTIMIZED = 3
    IGNORED = 4

    @classmethod
    def obj(cls):
        return {
            0: "无影响",
            1: "待确认",
            2: "需优化",
            3: "已优化",
            4: "已忽略",
        }


class ManualTestAutomationTypeEnum(BaseEnum):
    API = 0
    UI = 1
    PYTEST = 2

    @classmethod
    def obj(cls):
        return {0: "API自动化", 1: "UI自动化", 2: "Pytest自动化"}


class ManualTestRelationTypeEnum(BaseEnum):
    GENERATED = 0
    BOUND = 1
    MANUAL = 2

    @classmethod
    def obj(cls):
        return {0: "AI生成", 1: "绑定已有", 2: "手工维护"}


class ManualTestOptimizeStatusEnum(BaseEnum):
    NORMAL = 0
    NEED_OPTIMIZE = 1
    OPTIMIZING = 2
    OPTIMIZED = 3
    IGNORED = 4

    @classmethod
    def obj(cls):
        return {
            0: "正常",
            1: "需优化",
            2: "优化中",
            3: "已优化",
            4: "已忽略",
        }
