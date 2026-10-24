from src.common.enums.base import BaseEnum


class ApiProtocolTypeEnum(BaseEnum):
    """API协议类型"""
    HTTP = "http"
    SSE = "sse"
    JSON_RPC = "json_rpc"
    XML_RPC = "xml_rpc"
    SOAP = "soap"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    DUBBO = "dubbo"
    THRIFT = "thrift"
    MCP = "mcp"
    WEBSOCKET = "websocket"

    @classmethod
    def obj(cls):
        return {
            "http": "标准HTTP",
            "sse": "SSE事件流",
            "json_rpc": "JSON-RPC",
            "xml_rpc": "XML-RPC",
            "soap": "SOAP",
            "graphql": "GraphQL",
            "grpc": "gRPC",
            "dubbo": "Dubbo",
            "thrift": "Thrift",
            "mcp": "MCP",
            "websocket": "WebSocket",
        }
