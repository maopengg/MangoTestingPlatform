from src.common.enums.base import BaseEnum


class TestSuiteNoticeEnum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    NOT_SENT = 0
    SENT = 1
    EXPIRED = 2
    SENDING = 3

    @classmethod
    def obj(cls):
        return {
            cls.NOT_SENT.value: "等待发送",
            cls.SENT.value: "发送成功",
            cls.EXPIRED.value: "无需发送",
            cls.SENDING.value: "发送中",
        }
