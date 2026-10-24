from src.common.enums.base import BaseEnum


class DataFactoryEntityStatusChangeSourceEnum(BaseEnum):
    """数据工厂实体状态变更来源。"""
    UNKNOWN = 0
    PAGE_MANUAL = 1
    MCP = 2
    SCHEMA_MONITOR = 3
    SYSTEM_REPAIR = 4
    DATA_SYNC = 5

    @classmethod
    def obj(cls):
        return {
            0: "历史来源未知",
            1: "页面手动操作",
            2: "MCP 操作",
            3: "定时表结构巡检",
            4: "系统修复",
            5: "数据同步",
        }
