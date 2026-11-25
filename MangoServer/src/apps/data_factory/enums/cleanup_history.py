from src.common.enums.base import BaseEnum


class ResourceCleanupEventEnum(BaseEnum):
    STARTED = ('started', '开始清理')
    FAILED = ('failed', '清理失败')
    SUCCEEDED = ('succeeded', '清理验证成功')
    COMPENSATION_AUTHORIZED = ('compensation_authorized', '已授权精确补偿')
