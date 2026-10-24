from src.common.enums.base import BaseEnum


class AiMcpStatusEnum(BaseEnum):
    DISABLED = 0
    ENABLED = 1

    @classmethod
    def obj(cls):
        return {0: "停用", 1: "启用"}


class AiMcpTransportTypeEnum(BaseEnum):
    STREAMABLE_HTTP = 0
    SSE = 1
    STDIO = 2

    @classmethod
    def obj(cls):
        return {0: "Streamable HTTP", 1: "SSE", 2: "STDIO"}


class AiMcpAuthTypeEnum(BaseEnum):
    NONE = 0
    BEARER = 1
    API_KEY = 2

    @classmethod
    def obj(cls):
        return {0: "无鉴权", 1: "Bearer Token", 2: "API Key"}


class AiMcpUseTypeEnum(BaseEnum):
    PLATFORM = 0
    API_AUTOMATION = 1
    COMMON = 2

    @classmethod
    def obj(cls):
        return {0: "平台调用", 1: "API自动化", 2: "通用"}


class AiMcpToolRiskLevelEnum(BaseEnum):
    READ = 0
    PREVIEW = 1
    WRITE = 2
    EXECUTE = 3
    DELETE = 4

    @classmethod
    def obj(cls):
        return {
            0: "查询",
            1: "预览",
            2: "写入",
            3: "执行",
            4: "删除/清理",
        }
