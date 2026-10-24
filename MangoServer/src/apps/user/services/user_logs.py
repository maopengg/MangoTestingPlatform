"""用户操作日志写入服务。"""

from src.apps.user.models import UserLogs
from src.common.database import ModelMutationValidationError, save_model


class UserLogService:
    @staticmethod
    def record(payload: dict) -> UserLogs | None:
        try:
            return save_model(UserLogs, payload)
        except ModelMutationValidationError:
            return None
