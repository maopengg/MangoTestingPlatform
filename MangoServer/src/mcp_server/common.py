from __future__ import annotations

import os
from typing import Any

import jwt
from django.conf import settings

from src.auto_test.auto_user.models import User


def ok(data: Any = None, message: str = "操作成功", warnings: list[str] | None = None) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
        "warnings": warnings or [],
    }


def fail(message: str, error_code: str = "MCP_ERROR", details: Any = None) -> dict:
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "details": details if details is not None else {},
    }


def get_http_headers() -> dict[str, str]:
    """Best-effort header extraction for both official MCP and FastMCP runtimes."""
    try:
        from fastmcp.server.dependencies import get_http_headers as _get_http_headers  # type: ignore

        return dict(_get_http_headers())
    except Exception:
        return {}


def get_token_payload() -> dict | None:
    headers = get_http_headers()
    token = (
        headers.get("authorization")
        or headers.get("Authorization")
        or os.getenv("MANGO_MCP_TOKEN")
    )
    if not token:
        return None
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1]
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
    except Exception:
        return None


def current_user(user_id: int | None = None) -> User:
    if user_id is not None:
        return User.objects.get(id=user_id)
    payload = get_token_payload()
    if payload and payload.get("id"):
        return User.objects.get(id=payload["id"])
    env_user_id = os.getenv("MANGO_MCP_USER_ID")
    if env_user_id:
        return User.objects.get(id=env_user_id)
    raise ValueError("无法识别当前用户，请通过 Bearer token 或 user_id 提供用户上下文")


def environment_title(environment_id: int | None) -> str | None:
    if environment_id is None:
        return None
    from src.enums.tools_enum import EnvironmentEnum

    return EnvironmentEnum.get_value(int(environment_id))


def parse_json_string(value: Any) -> Any:
    if value == "":
        return None
    return value

