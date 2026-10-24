from src.common.enums.base import BaseEnum


class FunctionalTestIterationStatusEnum(BaseEnum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3

    @classmethod
    def obj(cls):
        return {0: "未开始", 1: "进行中", 2: "已完成", 3: "已取消"}
