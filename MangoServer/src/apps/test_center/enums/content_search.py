from src.common.enums.base import BaseEnum


class ContentSearchKindEnum(BaseEnum):
    AUTOMATION = ('automation', '自动化执行结果')
    DATASOURCE = ('datasource', '数据源执行记录')


class ContentSearchStatusEnum(BaseEnum):
    RUNNING = ('running', '检索中')
    COMPLETED = ('completed', '检索完成')
    PARTIAL = ('partial', '检索不完整')
    CANCELLED = ('cancelled', '已取消')
    FAILED = ('failed', '检索失败')
