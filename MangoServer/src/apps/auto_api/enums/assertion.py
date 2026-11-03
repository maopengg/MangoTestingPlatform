from enum import Enum


class ApiDefaultAssertionCheck(str, Enum):
    HTTP_STATUS = 'http_status'
    GRAPHQL_ERRORS = 'graphql_errors'
    JSON_RPC_ERROR = 'json_rpc_error'
    XML_FAULT = 'xml_fault'
    MCP_RESULT = 'mcp_result'
    GRPC_STATUS = 'grpc_status'
    WEBSOCKET_CLOSE = 'websocket_close'
    WEBSOCKET_HANDSHAKE = 'websocket_handshake'

    @classmethod
    def get_option(cls):
        return [
            {'key': cls.HTTP_STATUS.value, 'title': 'HTTP / SSE 等 · 状态码为 2xx'},
            {'key': cls.GRAPHQL_ERRORS.value, 'title': 'GraphQL · errors 为空'},
            {'key': cls.JSON_RPC_ERROR.value, 'title': 'JSON-RPC · error 为空'},
            {'key': cls.XML_FAULT.value, 'title': 'SOAP / XML-RPC · 不含 Fault'},
            {'key': cls.MCP_RESULT.value, 'title': 'MCP · isError 不为 true'},
            {'key': cls.GRPC_STATUS.value, 'title': 'gRPC · 状态为 OK'},
            {'key': cls.WEBSOCKET_CLOSE.value, 'title': 'WebSocket · 正常关闭（1000 / 1001）'},
            {'key': cls.WEBSOCKET_HANDSHAKE.value, 'title': 'WebSocket · 握手及协议状态正常'},
        ]

    @classmethod
    def defaults(cls):
        return [item.value for item in cls]
