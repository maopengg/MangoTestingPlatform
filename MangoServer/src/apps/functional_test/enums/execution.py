from src.common.enums.base import BaseEnum


class FunctionalTestResultEnum(BaseEnum):
    UNEXECUTED = 0
    PASSED = 1
    FAILED = 2
    BLOCKED = 3
    SKIPPED = 4

    @classmethod
    def obj(cls):
        return {0: "未执行", 1: "通过", 2: "失败", 3: "阻塞", 4: "跳过"}
