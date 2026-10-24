import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_NOT_FOUND,
)
from src.apps.auto_pytest.models import PytestRepositoryCredential


class PytestRepositoryCredentialService:
    ALGORITHM = "fernet-sha256-v1"

    @staticmethod
    def _cipher() -> Fernet:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    @classmethod
    def encrypt(cls, *, secret: str, password: str | None = None) -> bytes:
        payload = json.dumps(
            {"secret": secret or "", "password": password or ""},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return cls._cipher().encrypt(payload)

    @classmethod
    def reveal(cls, credential: PytestRepositoryCredential | None) -> dict:
        if credential is None:
            return {"secret": "", "password": ""}
        try:
            value = cls._cipher().decrypt(bytes(credential.secret_ciphertext)).decode("utf-8")
            payload = json.loads(value)
        except (InvalidToken, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise AutoPytestError(PYTEST_REPOSITORY_NOT_FOUND) from error
        if not isinstance(payload, dict):
            raise AutoPytestError(PYTEST_REPOSITORY_NOT_FOUND)
        return {
            "secret": str(payload.get("secret") or ""),
            "password": str(payload.get("password") or ""),
        }

    @classmethod
    def set_secret(
            cls,
            credential: PytestRepositoryCredential,
            *,
            secret: str,
            password: str | None = None,
    ) -> PytestRepositoryCredential:
        credential.secret_ciphertext = cls.encrypt(secret=secret, password=password)
        credential.key_version = cls.ALGORITHM
        return credential
