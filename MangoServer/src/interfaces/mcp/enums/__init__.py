"""Machine-readable states owned by the MCP adapter."""

from src.common.enums.base import BaseEnum


class McpAuthErrorCode(BaseEnum):
    REQUIRED = "AUTH_REQUIRED"
    INVALID = "AUTH_INVALID"
    EXPIRED = "AUTH_EXPIRED"


__all__ = ["McpAuthErrorCode"]
