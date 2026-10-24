import uuid

import time
from django.conf import settings
from django.core import signing

from src.apps.auto_ui.enums.live_stream import LiveStreamRole


class LiveStreamTokenService:
    SALT = "mango.ui.live-stream.v1"
    PROTOCOL_VERSION = 1
    PUBLISHER_TTL = 24 * 60 * 60
    READY_TTL = 7 * 24 * 60 * 60

    @classmethod
    def issue(cls, claims: dict, role: LiveStreamRole | str) -> str:
        role_value = str(role.value if isinstance(role, LiveStreamRole) else role)
        issued_at = int(time.time())
        payload = {
            **claims,
            "role": role_value,
            "permissions": cls._permissions(role_value),
            "protocol_version": cls.PROTOCOL_VERSION,
            "issued_at": issued_at,
            "exp": issued_at + cls._ttl_for_role(role_value),
            "nonce": uuid.uuid4().hex,
            "token_id": str(uuid.uuid4()),
        }
        return signing.dumps(
            payload,
            key=settings.LIVE_STREAM_SIGNING_KEY,
            salt=cls.SALT,
            compress=True,
        )

    @classmethod
    def verify(
            cls,
            token: str,
            expected_role: LiveStreamRole | str,
            *,
            max_age: int | None = None,
    ) -> dict:
        role = expected_role.value if isinstance(expected_role, LiveStreamRole) else expected_role
        ttl = max_age or cls._ttl_for_role(role)
        claims = cls._loads_with_key_rotation(token, ttl)
        if claims.get("role") != role:
            raise signing.BadSignature("直播令牌角色不匹配")
        if claims.get("protocol_version") != cls.PROTOCOL_VERSION:
            raise signing.BadSignature("直播令牌协议版本不受支持")
        for key in ("issued_at", "exp", "nonce", "token_id"):
            if not claims.get(key):
                raise signing.BadSignature("直播令牌缺少必要声明")
        if int(claims["exp"]) < int(time.time()):
            raise signing.SignatureExpired("直播令牌已过期")
        return claims

    @classmethod
    def _ttl_for_role(cls, role: str) -> int:
        return {
            LiveStreamRole.PUBLISHER.value: cls.PUBLISHER_TTL,
            LiveStreamRole.READY.value: cls.READY_TTL,
        }.get(role, cls.READY_TTL)

    @staticmethod
    def _permissions(role: str) -> list[str]:
        return {
            LiveStreamRole.PUBLISHER.value: ["publish"],
            LiveStreamRole.READY.value: ["start"],
        }.get(role, [])

    @classmethod
    def _loads_with_key_rotation(cls, token: str, max_age: int) -> dict:
        keys = [settings.LIVE_STREAM_SIGNING_KEY]
        previous_key = getattr(settings, "LIVE_STREAM_PREVIOUS_SIGNING_KEY", "")
        if previous_key and previous_key not in keys:
            keys.append(previous_key)
        last_error = None
        for key in keys:
            try:
                return signing.loads(token, key=key, salt=cls.SALT, max_age=max_age)
            except signing.BadSignature as error:
                last_error = error
        raise last_error or signing.BadSignature("直播令牌签名无效")
