from typing import Any

SENSITIVE_KEYS = {"api_key", "authorization", "password", "cookie", "token", "secret"}


def mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value
