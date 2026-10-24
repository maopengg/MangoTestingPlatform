from src.common.enums.base import BaseEnum


class ManualTestSuiteStatusEnum(BaseEnum):
    UNSCHEDULED = 1
    SCHEDULED = 2
    DEVELOPING = 3
    PENDING_TEST = 4
    TESTING = 5
    TEST_COMPLETED = 6
    CANCELLED = 7
    PENDING_DEVELOPMENT = 8
    PENDING_RELEASE = 9
    RELEASED = 10

    @classmethod
    def obj(cls):
        return {
            1: "需求池", 2: "需求就绪", 3: "开发中", 4: "待提测",
            5: "测试中", 6: "PM验收", 7: "已取消", 8: "待开发",
            9: "待发布", 10: "已发布",
        }
