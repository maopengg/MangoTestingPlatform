from src.apps.user.models import User
from src.apps.user.selectors.querysets import UserQuerySelector


class UserApiKeyService:
    @staticmethod
    def ensure_sync_user():
        user = (
            UserQuerySelector.user()
            .exclude(api_key__isnull=True)
            .exclude(api_key="")
            .order_by("id")
            .first()
        )
        if user is not None:
            return user
        user = UserQuerySelector.user().order_by("id").first()
        if user is not None and not user.api_key:
            user.api_key = User.unique_api_key()
            user.save(update_fields=["api_key"])
        return user
