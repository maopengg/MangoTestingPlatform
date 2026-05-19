from __future__ import annotations

import os
from typing import Any

import jwt
from django.conf import settings
from jwt import exceptions

from src.auto_test.auto_user.models import User


MCP_AUTH_REQUIRED_MESSAGE = (
    "MCP 调用需要用户 APIKey。请到「系统管理 - 用户管理」复制或生成 MCP APIKey，"
    "并在 MCP 客户端请求头中配置 Authorization: Bearer <APIKey>。"
)


class McpAuthError(ValueError):
    def __init__(self, message: str, error_code: str = "AUTH_REQUIRED", details: Any = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details if details is not None else {}


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
        from mcp.server.lowlevel.server import request_ctx

        request = request_ctx.get().request
        if request is not None and hasattr(request, "headers"):
            return dict(request.headers)
    except Exception:
        pass

    try:
        from fastmcp.server.dependencies import get_http_headers as _get_http_headers  # type: ignore

        return dict(_get_http_headers())
    except Exception:
        return {}


def get_auth_token() -> str | None:
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
    token = token.strip()
    return token or None


def get_token_payload() -> dict | None:
    token = get_auth_token()
    if not token or token.startswith("mango_"):
        return None
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
    except Exception:
        return None


def user_from_auth_token() -> User:
    token = get_auth_token()
    if not token:
        raise McpAuthError(MCP_AUTH_REQUIRED_MESSAGE, "AUTH_REQUIRED")
    if token.startswith("mango_"):
        try:
            return User.objects.get(api_key=token)
        except User.DoesNotExist as exc:
            raise McpAuthError(
                "MCP APIKey 无效，请到「系统管理 - 用户管理」复制或重新生成 APIKey。",
                "AUTH_INVALID",
            ) from exc
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
    except exceptions.ExpiredSignatureError as exc:
        raise McpAuthError(
            "当前登录 token 已过期，请使用 MCP APIKey，或重新登录后更新 MCP 客户端 Authorization。",
            "AUTH_EXPIRED",
        ) from exc
    except Exception as exc:
        raise McpAuthError("Authorization 无效，请检查 MCP APIKey 或 JWT。", "AUTH_INVALID") from exc
    if not payload.get("id"):
        raise McpAuthError("Authorization 中缺少用户信息。", "AUTH_INVALID")
    try:
        return User.objects.get(id=payload["id"])
    except User.DoesNotExist as exc:
        raise McpAuthError("Authorization 对应用户不存在。", "AUTH_INVALID") from exc


def require_mcp_user() -> dict | None:
    try:
        user_from_auth_token()
    except McpAuthError as exc:
        return fail(str(exc), exc.error_code, exc.details)
    return None


def current_user(user_id: int | None = None) -> User:
    token = get_auth_token()
    if token:
        return user_from_auth_token()
    if user_id is not None and os.getenv("MANGO_MCP_ALLOW_USER_ID_AUTH", "").lower() in {"1", "true", "yes", "on"}:
        return User.objects.get(id=user_id)
    env_user_id = os.getenv("MANGO_MCP_USER_ID")
    if env_user_id:
        return User.objects.get(id=env_user_id)
    raise McpAuthError(MCP_AUTH_REQUIRED_MESSAGE, "AUTH_REQUIRED")


def environment_title(environment_id: int | None) -> str | None:
    if environment_id is None:
        return None
    from src.enums.tools_enum import EnvironmentEnum

    return EnvironmentEnum.get_value(int(environment_id))


def parse_json_string(value: Any) -> Any:
    if value == "":
        return None
    return value

