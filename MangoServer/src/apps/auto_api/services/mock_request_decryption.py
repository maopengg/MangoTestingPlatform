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

    @staticmethod
    def _cipher_for_key(key: str) -> Fernet:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    @classmethod
    def _reveal(cls, value: str) -> str:
        # 只用于读取旧版密文，新配置不再加密，也不再依赖系统密钥。
        keys = [settings.SECRET_KEY]
        version = str(settings.VERSION)
        if version and settings.SECRET_KEY.endswith(version):
            prefix = settings.SECRET_KEY[:-len(version)]
            keys.extend(f'{prefix}{old_version}' for old_version in ('7.1.1', '7.2.0', '7.2.1', '7.2.2'))
        for key in dict.fromkeys(keys):
            if not key:
                continue
            try:
                return cls._cipher_for_key(key).decrypt(value.encode("ascii")).decode("utf-8")
            except (InvalidToken, UnicodeError, ValueError):
                continue
        raise MockRequestDecryptionError(
            "MOCK_DECRYPT_CONFIG_ERROR",
            "Mock请求解密配置不可用，请重新填写 Encrypt Key 和 Verification Token 后保存",
        )

    @classmethod
    def _stored_value(cls, config: dict, field: str) -> str:
        if field in config:
            return str(config[field] or "")
        ciphertext = config.get(f"{field}_ciphertext")
        return cls._reveal(str(ciphertext)) if ciphertext else ""

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
        try:
            if not encrypt_key:
                encrypt_key = cls._stored_value(existing, "encrypt_key")
            if "verification_token" in value:
                verification_token = str(value.get("verification_token") or "").strip()
            else:
                verification_token = cls._stored_value(existing, "verification_token")
        except MockRequestDecryptionError as error:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=(error.message,)) from error
        if not encrypt_key:
            raise AutoApiError(MOCK_API_CONFIG_INVALID, value=("启用飞书事件解密时必须配置 Encrypt Key",))
        return {
            "type": cls.TYPE_LARK_EVENT,
            "encrypt_key": encrypt_key,
            "verification_token": verification_token,
        }

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
        try:
            return cls.runtime_config({"request_decryption": config})["request_decryption"]
        except MockRequestDecryptionError as error:
            # 详情允许重新录入密钥；运行时仍通过 runtime_config 严格拒绝无效密文。
            return {"type": cls.TYPE_LARK_EVENT, "encrypt_key": "", "verification_token": "",
                    "configuration_error": error.message}

    @classmethod
    def runtime_config(cls, config: dict | None) -> dict:
        runtime = copy.deepcopy(config or {})
        decryption = runtime.get("request_decryption") or {}
        if decryption.get("type") != cls.TYPE_LARK_EVENT:
            runtime["request_decryption"] = {"type": cls.TYPE_NONE}
            return runtime
        encrypt_key = cls._stored_value(decryption, "encrypt_key")
        if not encrypt_key.strip():
            raise MockRequestDecryptionError("MOCK_DECRYPT_CONFIG_ERROR", "Mock请求解密配置缺少 Encrypt Key，请重新填写后保存")
        runtime["request_decryption"] = {
            "type": cls.TYPE_LARK_EVENT,
            "encrypt_key": encrypt_key,
            "verification_token": cls._stored_value(decryption, "verification_token"),
        }
        return runtime

    @classmethod
    def decrypt_body(cls, body_text: str, config: dict | None, *, preserve_text: bool = False) -> tuple[str, Any]:
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
        return (plaintext.decode('utf-8') if preserve_text else
                json.dumps(body_json, ensure_ascii=False, separators=(",", ":"))), body_json
