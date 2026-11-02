from src.common.enums.base import BaseEnum


class McpTransportType(BaseEnum):
    STREAMABLE_HTTP = 0
    SSE = 1
    STDIO = 2

    @classmethod
    def obj(cls):
        return {0: "Streamable HTTP", 1: "SSE", 2: "STDIO"}
