from src.common.enums.base import BaseEnum


class EvaluationTargetTypeEnum(BaseEnum):
    API_CASE = ("api_case", "API Case")
    API_INFO = ("api_info", "接口管理")
    MCP_TOOL = ("mcp_tool", "MCP Tool")
    AI_AGENT = ("ai_agent", "AI Agent")
    SCRIPT = ("script", "Python 脚本")
    STATIC = ("static", "静态输出")

    @classmethod
    def get_option(cls, k="key", v="title"):
        return [item for item in super().get_option(k, v) if item[k] in (cls.API_INFO.value, cls.SCRIPT.value)]
