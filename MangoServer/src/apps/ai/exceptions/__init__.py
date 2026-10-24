"""Business exceptions owned by the AI app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class AiError(MangoServerError):
    pass


AI_SERVICE_ERROR = ErrorDefinition(code=42000, message='{}')
AI_MCP_SERVER_IMPORTED_API_BOUND = ErrorDefinition(
    code=42001,
    message='MCP服务已导入API自动化接口，请先删除或解绑对应接口后再删除',
)
AI_MCP_TOOL_IMPORTED_API_BOUND = ErrorDefinition(
    code=42002,
    message='MCP Tool已导入API自动化接口，请先删除或解绑对应接口后再删除',
)


def ai_service_error(message: str) -> AiError:
    return AiError(AI_SERVICE_ERROR, value=(message,))


__all__ = [
    "AI_MCP_SERVER_IMPORTED_API_BOUND",
    "AI_MCP_TOOL_IMPORTED_API_BOUND",
    "AI_SERVICE_ERROR",
    "AiError",
    "ai_service_error",
]
