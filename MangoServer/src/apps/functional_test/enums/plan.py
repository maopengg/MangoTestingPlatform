from src.common.enums.base import BaseEnum


class FunctionalTestPlanScopeTypeEnum(BaseEnum):
    REQUIREMENT = 0
    SPRINT = 1
    RELEASE = 2
    REGRESSION = 3
    AD_HOC = 4

    @classmethod
    def obj(cls):
        return {0: "需求", 1: "Sprint", 2: "发布", 3: "回归", 4: "临时测试"}


class FunctionalTestPlanStatusEnum(BaseEnum):
    DRAFT = 0
    READY = 1
    RUNNING = 2
    COMPLETED = 3
    CLOSED = 4

    @classmethod
    def obj(cls):
        return {0: "草稿", 1: "待执行", 2: "执行中", 3: "已完成", 4: "已关闭"}
