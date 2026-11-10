from src.common.enums.base import BaseEnum


class ApiResourceCleanupStatus(BaseEnum):
    PREPARED = 'prepared'
    SENT = 'sent'
    OWNED = 'owned'
    CLEANING = 'cleaning'
    CLEANED = 'cleaned'
    FAILED = 'failed'

    @classmethod
    def obj(cls):
        return {cls.PREPARED.value: '请求尚未发送', cls.SENT.value: '待核实创建结果',
                cls.OWNED.value: '已登记', cls.CLEANING.value: '清理中',
                cls.CLEANED.value: '已清理并验证', cls.FAILED.value: '清理未完成'}
