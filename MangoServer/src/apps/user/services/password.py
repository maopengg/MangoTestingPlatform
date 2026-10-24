import secrets

from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from mangotools.data_processor import EncryptionTool


def double_md5(value: str) -> str:
    first = EncryptionTool.md5_32_small(value)
    return EncryptionTool.md5_32_small(first)


def encode_plain_password(password: str) -> str:
    """Hash the credential digest expected by existing web and actuator clients."""
    return make_password(double_md5(password))


def verify_password_digest(password_digest: str | None, stored_password: str | None) -> tuple[bool, str | None]:
    """Verify a client digest and return an upgraded hash for legacy rows."""
    if not password_digest or not stored_password:
        return False, None
    try:
        identify_hasher(stored_password)
    except ValueError:
        valid = secrets.compare_digest(str(password_digest), str(stored_password))
        return valid, make_password(password_digest) if valid else None
    return check_password(password_digest, stored_password), None
