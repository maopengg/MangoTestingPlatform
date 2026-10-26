import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_NOT_FOUND,
    PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED,
)
from src.apps.auto_pytest.enums import PytestRepositoryCredentialTypeEnum
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

    @classmethod
    def save_from_request(cls, data: dict, credential, *, operator_id=None):
        secret = str(data.get("credential_secret") or "")
        if "credential_auth_type" in data:
            auth_type = str(data.get("credential_auth_type") or "none").strip() or "none"
        else:
            auth_type = credential.auth_type if credential else ("token" if secret else "none")
        if auth_type == "none":
            return None
        if auth_type not in PytestRepositoryCredentialTypeEnum.obj():
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        if not secret and (credential is None or credential.auth_type != auth_type):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        username = str(data.get("credential_username", getattr(credential, "username", "")) or "").strip()
        if auth_type == "username_password" and not username:
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        if credential is None:
            credential = PytestRepositoryCredential(create_user_id=operator_id)
        credential.auth_type = auth_type
        credential.username = username if auth_type == "username_password" else None
        credential.update_user_id = operator_id
        if secret:
            cls.set_secret(
                credential,
                secret=secret if auth_type == "token" else "",
                password=secret if auth_type == "username_password" else "",
            )
        credential.save()
        return credential
