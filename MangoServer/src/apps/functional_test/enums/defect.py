from src.common.enums.base import BaseEnum


class FunctionalTestDefectSourceEnum(BaseEnum):
    PLAN = 0
    CASE_LIBRARY = 1
    EXPLORATORY = 2
    PRODUCTION = 3
    USER_FEEDBACK = 4
    OTHER = 5
    AUTOMATION_REQUIREMENT = 6
    AUTOMATION_REGRESSION = 7

    @classmethod
    def obj(cls):
        return {
            0: "测试计划", 1: "用例库", 2: "探索测试", 3: "生产反馈", 4: "用户反馈", 5: "其他",
            6: "自动化发现（本迭代需求）", 7: "自动化发现（回归测试）",
        }


class FunctionalTestDefectTypeEnum(BaseEnum):
    FUNCTIONAL = 0
    UI = 1
    COMPATIBILITY = 2
    PERFORMANCE = 3
    SECURITY = 4
    DATA = 5
    OTHER = 6

    @classmethod
    def obj(cls):
        return {0: "功能问题", 1: "界面问题", 2: "兼容性问题", 3: "性能问题", 4: "安全问题", 5: "数据问题", 6: "其他"}


class FunctionalTestDefectSeverityEnum(BaseEnum):
    FATAL = 0
    SERIOUS = 1
    NORMAL = 2
    MINOR = 3
    SUGGESTION = 4

    @classmethod
    def obj(cls):
        return {0: "致命", 1: "严重", 2: "一般", 3: "轻微", 4: "建议"}


class FunctionalTestDefectPriorityEnum(BaseEnum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @classmethod
    def obj(cls):
        return {0: "P0", 1: "P1", 2: "P2", 3: "P3"}


class FunctionalTestDefectStatusEnum(BaseEnum):
    NEW = 0
    CONFIRMED = 1
    PROCESSING = 2
    RESOLVED = 3
    CLOSED = 4
    REOPENED = 5

    @classmethod
    def obj(cls):
        return {0: "新建", 1: "已确认", 2: "处理中", 3: "已解决", 4: "已关闭", 5: "已重新打开"}


class FunctionalTestDefectResolutionEnum(BaseEnum):
    FIXED = 0
    NOT_A_DEFECT = 1
    DUPLICATE = 2
    CANNOT_REPRODUCE = 3
    WONT_FIX = 4
    AS_DESIGNED = 5

    @classmethod
    def obj(cls):
        return {0: "已修复", 1: "非缺陷", 2: "重复缺陷", 3: "无法复现", 4: "暂不处理", 5: "设计如此"}
