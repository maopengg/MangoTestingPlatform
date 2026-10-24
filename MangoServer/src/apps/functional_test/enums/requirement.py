from src.common.enums.base import BaseEnum


class FunctionalTestRequirementStatusEnum(BaseEnum):
    ACTIVE = 1
    COMPLETED = 2
    CANCELLED = 3

    @classmethod
    def obj(cls):
        return {1: "有效", 2: "已完成", 3: "已取消"}


class FunctionalTestRequirementIssueTypeEnum(BaseEnum):
    USER_STORY = 0
    TASK = 1
    BUG_FIX = 2
    TECHNICAL = 3

    @classmethod
    def obj(cls):
        return {0: "User Story", 1: "Task", 2: "Bug Fix", 3: "Technical"}


class FunctionalTestRequirementCategoryEnum(BaseEnum):
    PRODUCT_ITERATION = 0
    CUSTOMER_REQUIREMENT = 1
    AI = 2
    ONCALL = 3
    TECHNICAL_DEBT = 4

    @classmethod
    def obj(cls):
        return {0: "产品迭代", 1: "客户需求", 2: "AI", 3: "Oncall转", 4: "技术债/技术优化"}


class FunctionalRequirementTaskTypeEnum(BaseEnum):
    PRODUCT = 0
    FRONTEND = 1
    BACKEND = 2
    DATA = 3
    INTEGRATION = 4
    QA = 5
    UI = 6
    RELEASE = 7
    OTHER = 8

    @classmethod
    def obj(cls):
        return {0: "产品", 1: "前端", 2: "后端", 3: "数据", 4: "联调", 5: "QA", 6: "UI", 7: "发布", 8: "其他"}


class FunctionalRequirementTaskStatusEnum(BaseEnum):
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3

    @classmethod
    def obj(cls):
        return {0: "待开始", 1: "进行中", 2: "已完成", 3: "已取消"}


class FunctionalRequirementSelfTestStatusEnum(BaseEnum):
    NOT_STARTED = 0
    PASSED = 1
    FAILED = 2
    NOT_APPLICABLE = 3

    @classmethod
    def obj(cls):
        return {0: "未开始", 1: "已通过", 2: "失败", 3: "不适用"}
