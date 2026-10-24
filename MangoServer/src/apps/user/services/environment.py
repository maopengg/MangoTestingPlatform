from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.user.exceptions import (
    USER_TEST_ENVIRONMENT_NOT_FOUND,
    UserError,
)
from src.apps.user.models import User
from src.apps.user.services.user_cache import UserCacheService


class UserEnvironmentService:
    """用户当前测试环境的统一读写入口。"""

    @classmethod
    def switch(
            cls,
            user: User,
            environment_id,
            *,
            operator_id: int | None = None,
    ) -> dict:
        normalized = cls.normalize_environment(environment_id)
        UserCacheService.set_selected_environment(user, normalized)
        user.update_user_id = operator_id or user.id
        user.save(
            update_fields=[
                "config",
                "update_user",
                "update_time",
            ]
        )
        return {
            "user": user,
            "user_id": user.id,
            "selected_environment": normalized,
            "selected_environment_title": cls.environment_title(normalized),
        }

    @staticmethod
    def normalize_environment(environment_id) -> int | None:
        if environment_id in (None, ""):
            return None
        try:
            normalized = int(environment_id)
        except (TypeError, ValueError) as error:
            raise UserError(USER_TEST_ENVIRONMENT_NOT_FOUND, error=str(error)) from error
        if normalized not in EnvironmentEnum.get_key_list():
            raise UserError(USER_TEST_ENVIRONMENT_NOT_FOUND)
        return normalized

    @staticmethod
    def environment_title(environment_id: int | None) -> str:
        if environment_id is None:
            return "未选择测试环境"
        return EnvironmentEnum.obj().get(environment_id, str(environment_id))
