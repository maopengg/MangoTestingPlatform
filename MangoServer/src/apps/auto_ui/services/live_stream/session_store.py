from src.apps.auto_ui.exceptions import (
    AUTO_UI_LIVE_STREAM_SESSION_STORE_NOT_FOUND,
    AutoUiError,
)

from src.apps.auto_ui.models import UiLiveStreamSession
from src.apps.user.models import User


class LiveStreamSessionStore:
    OPEN_STATUS = 0
    CLOSED_STATUS = 1

    @classmethod
    def create(cls, claims: dict) -> UiLiveStreamSession:
        user = User.objects.get(id=int(claims["user_id"]))
        session, _ = UiLiveStreamSession.objects.update_or_create(
            stream_id=claims["stream_id"],
            defaults={
                "user": user,
                "executor_username": claims["executor_username"],
                "connection_id": claims["connection_id"],
                "execution_type": claims["execution_type"],
                "execution_id": claims["execution_id"],
                "resource_id": claims["resource_id"],
                "read_only": bool(claims.get("read_only")),
                "status": cls.OPEN_STATUS,
                "claims": claims,
            },
        )
        return session

    @classmethod
    def get_claims(cls, stream_id: str) -> dict:
        try:
            session = UiLiveStreamSession.objects.get(stream_id=stream_id, status=cls.OPEN_STATUS)
        except UiLiveStreamSession.DoesNotExist as error:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_SESSION_STORE_NOT_FOUND) from error
        claims = dict(session.claims or {})
        claims.update(
            {
                "stream_id": session.stream_id,
                "user_id": session.user_id,
                "executor_username": session.executor_username,
                "connection_id": session.connection_id,
                "execution_type": session.execution_type,
                "execution_id": session.execution_id,
                "resource_id": session.resource_id,
                "read_only": session.read_only,
            }
        )
        return claims

    @classmethod
    def close(cls, stream_id: str) -> None:
        UiLiveStreamSession.objects.filter(stream_id=stream_id).delete()
