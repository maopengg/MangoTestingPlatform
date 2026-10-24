from src.apps.user.models import (
    User,
    UserLogs,
)


class UserQuerySelector:
    @staticmethod
    def user():
        return User.objects.all()

    @staticmethod
    def user_logs():
        return UserLogs.objects.all()
