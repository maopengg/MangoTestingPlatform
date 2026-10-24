"""MCP adapter exceptions."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class McpError(MangoServerError):
    pass


class McpAuthError(McpError):
    """Expected MCP authentication failure handled at the adapter boundary."""


MCP_TEST_ENVIRONMENT_REQUIRED = ErrorDefinition(
    code=43000,
    message="当前用户未选择测试环境，请先调用 switch_user_test_environment。",
)
MCP_ASSERTION_METHOD_NOT_FOUND = ErrorDefinition(code=43001, message="断言方法不存在：{}")
MCP_PLAYWRIGHT_CODE_INVALID = ErrorDefinition(code=43002, message="Playwright 代码解析失败：{}")
MCP_FILE_BASE64_INVALID = ErrorDefinition(code=43003, message="content_base64 不是合法的 base64 内容")
MCP_IMPORTED_STEP_INVALID = ErrorDefinition(code=43004, message="Playwright 步骤配置错误：{}")
MCP_AUTHORIZATION_REQUIRED = ErrorDefinition(
    code=43005,
    message=(
        "服务端未获取到 MCP Authorization 请求头。请确认客户端已配置 "
        "Authorization: Bearer <APIKey>；如果确认已经发送，请联系管理员检查网关或 MCP 认证上下文。"
        "MCP APIKey 永久有效，不会自动过期，仅在用户手动重置后失效。"
    ),
)
MCP_API_KEY_INVALID = ErrorDefinition(
    code=43006,
    message=(
        "服务端已收到 MCP APIKey，但在当前环境中未找到匹配用户。MCP APIKey 永久有效，不会自动过期；"
        "请检查是否复制错误、是否使用了其他环境的 APIKey，或该 APIKey 是否被用户手动重置。"
    ),
)
MCP_JWT_EXPIRED = ErrorDefinition(
    code=43007,
    message=(
        "当前登录 JWT 已过期。请重新登录后更新 MCP 客户端 Authorization；"
        "如需长期调用，请使用永久有效的 MCP APIKey。"
    ),
)
MCP_JWT_INVALID = ErrorDefinition(
    code=43008,
    message=(
        "服务端已收到登录 JWT，但 JWT 无效或已过期。登录 JWT 有有效期，请重新登录后更新 Authorization；"
        "如需长期调用，请改用永久有效的 MCP APIKey。"
    ),
)
MCP_AUTH_USER_ID_REQUIRED = ErrorDefinition(code=43009, message="Authorization 中缺少用户信息。")
MCP_AUTH_USER_NOT_FOUND = ErrorDefinition(code=43010, message="Authorization 对应用户不存在。")
