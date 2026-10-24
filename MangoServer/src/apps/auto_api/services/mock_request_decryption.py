import base64
import copy
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings

from src.apps.auto_api.exceptions import (
    AutoApiError,
    MOCK_API_CONFIG_INVALID,
    MockRequestDecryptionError,
)


class MockRequestDecryptionService:
    TYPE_NONE = "none"
    TYPE_LARK_EVENT = "lark_event"
    SUPPORTED_TYPES = {TYPE_NONE, TYPE_LARK_EVENT}
    STORAGE_ALGORITHM = "fernet-sha256-v1"

    @staticmethod
    def _cipher() -> Fernet:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    @classmethod
    def _seal(cls, value: str) -> str:
        return cls._cipher().encrypt(value.encode("utf-8")).decode("ascii")

    @classmethod
    def _reveal(cls, value: str) -> str:
        try:
            return cls._cipher().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as error:
            raise MockRequestDecryptionError(
                "MOCK_DECRYPT_CONFIG_ERROR",
                "Mock请求解密配置不可用，请重新保存解密密钥",
            ) from error

    @classmethod
    def normalize_for_storage(cls, value: Any, existing_config: dict | None = None) -> dict:
        if value in (None, ""):
            value = {"type": cls.TYPE_NONE}
        if not isinstance(value, dict):
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求解密配置必须是JSON对象",))
        decrypt_type = str(value.get("type") or cls.TYPE_NONE).strip()
        if decrypt_type not in cls.SUPPORTED_TYPES:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("请求解密类型不支持",))
        if decrypt_type == cls.TYPE_NONE:
            return {"type": cls.TYPE_NONE}

        existing = (existing_config or {}).get("request_decryption") or {}
        encrypt_key = str(value.get("encrypt_key") or "").strip()
        verification_token = str(value.get("verification_token") or "").strip()
        encrypt_key_ciphertext = (
            cls._seal(encrypt_key)
            if encrypt_key
            else str(existing.get("encrypt_key_ciphertext") or "")
        )
        verification_token_ciphertext = (
            cls._seal(verification_token)
            if verification_token
            else str(existing.get("verification_token_ciphertext") or "")
        )
        if not encrypt_key_ciphertext:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("启用飞书事件解密时必须配置 Encrypt Key",))
        result = {
            "type": cls.TYPE_LARK_EVENT,
            "storage_algorithm": cls.STORAGE_ALGORITHM,
            "encrypt_key_ciphertext": encrypt_key_ciphertext,
        }
        if verification_token_ciphertext:
            result["verification_token_ciphertext"] = verification_token_ciphertext
        return result

    @classmethod
    def editable_config(cls, value: Any) -> dict:
        config = value if isinstance(value, dict) else {}
        decrypt_type = str(config.get("type") or cls.TYPE_NONE)
        if decrypt_type != cls.TYPE_LARK_EVENT:
            return {
                "type": cls.TYPE_NONE,
                "encrypt_key": "",
                "verification_token": "",
            }
        return {
            "type": cls.TYPE_LARK_EVENT,
            "encrypt_key": cls._reveal(str(config.get("encrypt_key_ciphertext") or "")),
            "verification_token": cls._reveal(str(config.get("verification_token_ciphertext") or ""))
            if config.get("verification_token_ciphertext")
            else "",
        }

    @classmethod
    def runtime_config(cls, config: dict | None) -> dict:
        runtime = copy.deepcopy(config or {})
        decryption = runtime.get("request_decryption") or {}
        if decryption.get("type") != cls.TYPE_LARK_EVENT:
            runtime["request_decryption"] = {"type": cls.TYPE_NONE}
            return runtime
        runtime["request_decryption"] = {
            "type": cls.TYPE_LARK_EVENT,
            "encrypt_key": cls._reveal(str(decryption.get("encrypt_key_ciphertext") or "")),
            "verification_token": cls._reveal(str(decryption.get("verification_token_ciphertext") or ""))
            if decryption.get("verification_token_ciphertext")
            else "",
        }
        return runtime

    @classmethod
    def decrypt_body(cls, body_text: str, config: dict | None) -> tuple[str, Any]:
        decryption = config or {}
        if decryption.get("type") != cls.TYPE_LARK_EVENT:
            try:
                return body_text, json.loads(body_text) if body_text else None
            except (TypeError, ValueError):
                return body_text, None

        try:
            envelope = json.loads(body_text)
        except (TypeError, ValueError) as error:
            raise MockRequestDecryptionError(
                "MOCK_ENCRYPTED_BODY_INVALID",
                "请求体不是合法JSON，无法执行飞书事件解密",
            ) from error
        encrypted = envelope.get("encrypt") if isinstance(envelope, dict) else None
        if not isinstance(encrypted, str) or not encrypted:
            raise MockRequestDecryptionError(
                "MOCK_ENCRYPTED_BODY_INVALID",
                "请求体缺少 encrypt 字段，无法执行飞书事件解密",
            )
        try:
            encrypted_bytes = base64.b64decode(encrypted, validate=True)
            if len(encrypted_bytes) <= 16:
                raise ValueError("encrypted body is too short")
            key = hashlib.sha256(str(decryption.get("encrypt_key") or "").encode("utf-8")).digest()
            decryptor = Cipher(algorithms.AES(key), modes.CBC(encrypted_bytes[:16])).decryptor()
            padded = decryptor.update(encrypted_bytes[16:]) + decryptor.finalize()
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            plaintext = unpadder.update(padded) + unpadder.finalize()
            body_json = json.loads(plaintext.decode("utf-8"))
        except Exception as error:
            raise MockRequestDecryptionError(
                "MOCK_REQUEST_DECRYPT_FAILED",
                "飞书事件请求解密失败，请检查 Encrypt Key",
            ) from error
        if not isinstance(body_json, dict):
            raise MockRequestDecryptionError(
                "MOCK_DECRYPTED_BODY_INVALID",
                "飞书事件解密结果不是JSON对象",
            )
        expected_token = str(decryption.get("verification_token") or "")
        header = body_json.get("header") if isinstance(body_json.get("header"), dict) else {}
        actual_token = body_json.get("token") or header.get("token")
        if expected_token and actual_token != expected_token:
            raise MockRequestDecryptionError(
                "MOCK_VERIFICATION_TOKEN_MISMATCH",
                "飞书事件 Verification Token 校验失败",
            )
        return json.dumps(body_json, ensure_ascii=False, separators=(",", ":")), body_json
