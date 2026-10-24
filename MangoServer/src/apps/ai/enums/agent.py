from src.common.enums.base import BaseEnum


class AiAgentTaskTypeEnum(BaseEnum):
    FEISHU_IMPORT = 0
    MANUAL_CASE_SYNC = 1
    GENERATE_API_CASE = 2

    @classmethod
    def obj(cls):
        return {0: "飞书文档解析", 1: "同步功能测试Case", 2: "生成API自动化"}


class AiAgentTaskStatusEnum(BaseEnum):
    FAIL = 0
    SUCCESS = 1
    PENDING = 2
    RUNNING = 3
    WAITING_CONFIRM = 4
    PARTIAL_SUCCESS = 5
    CANCELLED = 6
    CLAIMED = 7
    WAITING_MODEL = 8

    @classmethod
    def obj(cls):
        return {
            0: "失败",
            1: "成功",
            2: "待开始",
            3: "运行中",
            4: "等待确认",
            5: "部分成功",
            6: "已取消",
            7: "已领取",
            8: "等待模型",
        }


class AiAgentToolCallStatusEnum(BaseEnum):
    FAIL = 0
    SUCCESS = 1

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "成功"}
