import jwt
from channels.db import database_sync_to_async
from django.conf import settings
from jwt import exceptions

from src.apps.user.selectors.querysets import UserQuerySelector


class RealtimeJwtAuthentication:
    @staticmethod
    @database_sync_to_async
    def authenticate(token: str) -> dict:
        if not token:
            raise RuntimeError("未提供 token")
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
        except exceptions.ExpiredSignatureError as error:
            raise RuntimeError("当前用户登录已过期，请重新登录") from error
        except jwt.DecodeError as error:
            raise RuntimeError("token 无效，请检查后重试") from error
        except jwt.InvalidTokenError as error:
            raise RuntimeError("token 非法，请使用有效的 token") from error
        user = UserQuerySelector.user().get(id=payload.get("id"))
        return {
            "id": int(user.id),
            "username": user.username,
            "name": user.name,
            "client_type": payload.get("client_type"),
        }
