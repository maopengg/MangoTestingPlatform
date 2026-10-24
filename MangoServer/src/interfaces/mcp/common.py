from __future__ import annotations

import json
import os
import secrets
import threading
from contextvars import ContextVar, Token
from typing import Any

import jwt
from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections
from jwt import exceptions

from src.apps.user.models import User
from src.apps.user.selectors.querysets import UserQuerySelector
from src.interfaces.mcp.enums import McpAuthErrorCode
from src.interfaces.mcp.exceptions import (
    MCP_API_KEY_INVALID,
    MCP_AUTH_USER_ID_REQUIRED,
    MCP_AUTH_USER_NOT_FOUND,
    MCP_AUTHORIZATION_REQUIRED,
    MCP_JWT_EXPIRED,
    MCP_JWT_INVALID,
    McpAuthError,
)

_MCP_AUTHORIZATION_HEADER: ContextVar[str | None] = ContextVar(
    "mcp_authorization_header",
    default=None,
)


def ok(data: Any = None, message: str = "操作成功", warnings: list[str] | None = None) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
        "warnings": warnings or [],
    }


def normalize_pagination(page: int = 1, page_size: int = 10, max_page_size: int = 10) -> tuple[int, int]:
    try:
        page = max(int(page or 1), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(max(int(page_size or 10), 1), max_page_size)
    except (TypeError, ValueError):
        page_size = min(20, max_page_size)
    return page, page_size


def paginate_queryset(queryset, page: int = 1, page_size: int = 10, max_page_size: int = 10):
    page, page_size = normalize_pagination(page, page_size, max_page_size)
    count = queryset.count()
    offset = (page - 1) * page_size
    return queryset[offset: offset + page_size], count, page, page_size


def paginate_list(items: list, page: int = 1, page_size: int = 10, max_page_size: int = 10):
    page, page_size = normalize_pagination(page, page_size, max_page_size)
    count = len(items)
    offset = (page - 1) * page_size
    return items[offset: offset + page_size], count, page, page_size


def fail(message: str, error_code: str = "MCP_ERROR", details: Any = None) -> dict:
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "details": details if details is not None else {},
    }


def get_http_headers(
        include_all: bool = False,
        include: set[str] | None = None,
) -> dict[str, str]:
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

        return dict(_get_http_headers(include_all=include_all, include=include))
    except Exception:
        return {}


def bind_authorization_header(value: str | None) -> Token:
    return _MCP_AUTHORIZATION_HEADER.set(value)


def reset_authorization_header(token: Token) -> None:
    _MCP_AUTHORIZATION_HEADER.reset(token)


def get_mcp_request_info() -> dict:
    """Best-effort request metadata extraction for MCP tool logs."""
    try:
        from mcp.server.lowlevel.server import request_ctx

        request = request_ctx.get().request
        if request is None:
            return {}
        client = getattr(request, "client", None)
        return {
            "path": getattr(request, "url", None).path if getattr(request, "url", None) else "/mcp",
            "method": getattr(request, "method", "POST"),
            "client_ip": getattr(client, "host", None),
        }
    except Exception:
        return {}


def get_auth_token() -> str | None:
    # FastMCP 3 excludes Authorization by default because get_http_headers()
    # is also used for forwarding headers to downstream services.
    headers = get_http_headers(include={"authorization"})
    token = (
            _MCP_AUTHORIZATION_HEADER.get()
            or
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
        raise McpAuthError(
            MCP_AUTHORIZATION_REQUIRED,
            error_code=McpAuthErrorCode.REQUIRED.value,
        )
    if token.startswith("mango_"):
        try:
            return UserQuerySelector.user().get(api_key=token)
        except User.DoesNotExist as exc:
            raise McpAuthError(MCP_API_KEY_INVALID, error_code=McpAuthErrorCode.INVALID.value) from exc
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
    except exceptions.ExpiredSignatureError as exc:
        raise McpAuthError(
            MCP_JWT_EXPIRED,
            error_code=McpAuthErrorCode.EXPIRED.value,
        ) from exc
    except Exception as exc:
        raise McpAuthError(MCP_JWT_INVALID, error_code=McpAuthErrorCode.INVALID.value) from exc
    if not payload.get("id"):
        raise McpAuthError(MCP_AUTH_USER_ID_REQUIRED, error_code=McpAuthErrorCode.INVALID.value)
    try:
        return UserQuerySelector.user().get(id=payload["id"])
    except User.DoesNotExist as exc:
        raise McpAuthError(MCP_AUTH_USER_NOT_FOUND, error_code=McpAuthErrorCode.INVALID.value) from exc


def require_mcp_user() -> dict | None:
    try:
        user_from_auth_token()
    except McpAuthError as exc:
        return fail(exc.msg, exc.error_code, exc.details)
    return None


def current_user(user_id: int | None = None) -> User:
    token = get_auth_token()
    if token:
        return user_from_auth_token()
    if user_id is not None and os.getenv("MANGO_MCP_ALLOW_USER_ID_AUTH", "").lower() in {"1", "true", "yes", "on"}:
        return UserQuerySelector.user().get(id=user_id)
    env_user_id = os.getenv("MANGO_MCP_USER_ID")
    if env_user_id:
        return UserQuerySelector.user().get(id=env_user_id)
    raise McpAuthError(
        MCP_AUTHORIZATION_REQUIRED,
        error_code=McpAuthErrorCode.REQUIRED.value,
    )


def create_dangerous_action_preview(
        action: str,
        target_id: int | str,
        confirm_text: str,
        impact: dict,
        ttl_seconds: int = 600,
) -> dict:
    """Create a short-lived confirmation token for high-risk MCP actions."""
    user = current_user()
    preview_token = secrets.token_urlsafe(24)
    cache_key = f"mcp:dangerous:{user.id}:{action}:{target_id}:{preview_token}"
    cache.set(
        cache_key,
        {
            "user_id": user.id,
            "action": action,
            "target_id": str(target_id),
            "confirm_text": confirm_text,
            "impact": impact,
        },
        ttl_seconds,
    )
    return {
        "action": action,
        "target_id": target_id,
        "operator_user_id": user.id,
        "impact": impact,
        "preview_token": preview_token,
        "confirm_text": confirm_text,
        "expires_in_seconds": ttl_seconds,
        "next_step": "请用户阅读 impact 后，原样传回 preview_token 和 confirm_text 执行危险操作。",
    }


def validate_dangerous_action_confirmation(
        action: str,
        target_id: int | str,
        preview_token: str | None,
        confirm_text: str | None,
) -> dict | None:
    """Validate and consume a preview token before high-risk MCP actions."""
    if not preview_token or not confirm_text:
        return fail(
            "危险操作必须先调用对应 preview_*_impact 工具，并传回 preview_token 和 confirm_text。",
            "PREVIEW_REQUIRED",
        )
    user = current_user()
    cache_key = f"mcp:dangerous:{user.id}:{action}:{target_id}:{preview_token}"
    payload = cache.get(cache_key)
    if not payload:
        return fail("预览确认已过期或不存在，请重新调用 preview_*_impact。", "PREVIEW_EXPIRED")
    if payload.get("confirm_text") != confirm_text:
        return fail("confirm_text 不匹配，请原样使用预览结果中的确认文案。", "CONFIRM_TEXT_MISMATCH")
    cache.delete(cache_key)
    return None


def _redact_sensitive(value: Any) -> Any:
    sensitive_keys = {
        "authorization",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "password",
        "cache_data",
        "content_base64",
        "custom_code",
        "preview_token",
    }
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(sensitive in key_text for sensitive in sensitive_keys):
                redacted[key] = "***"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _json_dumps_limited(value: Any, limit: int = 2000) -> str:
    try:
        return json.dumps(_redact_sensitive(value), ensure_ascii=False, default=str)[:limit]
    except Exception:
        return str(value)[:limit]


def log_mcp_tool_call_async(
        tool_name: str,
        arguments: dict | None,
        result: Any,
        status_code: int = 200,
        user: User | None = None,
) -> None:
    """Write MCP tool call logs to the same user_logs table used by HTTP middleware."""
    headers = get_http_headers()
    request_info = get_mcp_request_info()
    user_id = user.id if user else None

    def _save():
        try:
            from src.apps.user.services.user_logs import UserLogService
            from src.apps.system.enums import ClientTypeEnum

            response_payload = result
            if isinstance(result, dict) and "success" in result:
                response_payload = {key: value for key, value in result.items() if key != "data"}
            log_entry = {
                "user": user_id,
                "source_type": ClientTypeEnum.MCP.value,
                "ip": request_info.get("client_ip")
                      or headers.get("x-forwarded-for")
                      or headers.get("X-Forwarded-For"),
                "url": f"{request_info.get('path') or '/mcp'}#{tool_name}"[:256],
                "method": request_info.get("method") or "POST",
                "status_code": str(status_code),
                "request_data": _json_dumps_limited({"tool": tool_name, "arguments": arguments or {}}),
                "response_data": _json_dumps_limited(response_payload),
            }
            close_old_connections()
            if log_entry["user"] and not UserQuerySelector.user().filter(id=log_entry["user"]).exists():
                log_entry["user"] = None
            UserLogService.record(log_entry)
        except Exception:
            pass
        finally:
            close_old_connections()

    thread = threading.Thread(target=_save)
    thread.daemon = True
    thread.start()


def environment_title(environment_id: int | None) -> str | None:
    if environment_id is None:
        return None
    from src.apps.test_center.enums.environment import EnvironmentEnum

    return EnvironmentEnum.get_value(int(environment_id))


def parse_json_string(value: Any) -> Any:
    if value == "":
        return None
    return value
