# -*- coding: utf-8 -*-
from dataclasses import dataclass
from http import HTTPStatus
from xml.etree import ElementTree

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.schemas.execution import ApiExecutionResponse


@dataclass(frozen=True)
class ProtocolCallOutcome:
    success: bool
    protocol_status: str
    error_message: str | None = None

    def result_fields(self) -> dict:
        return {
            'call_success': self.success,
            'protocol_status': self.protocol_status,
            'status': StatusEnum.SUCCESS.value if self.success else StatusEnum.FAIL.value,
            'error_msg': self.error_message,
        }


class ProtocolCallOutcomeService:
    """按协议判断接口是否真正调用成功，不把业务响应字段当作协议状态。"""

    HTTP_PROTOCOLS = {
        ApiProtocolTypeEnum.HTTP.value,
        ApiProtocolTypeEnum.SSE.value,
        ApiProtocolTypeEnum.JSON_RPC.value,
        ApiProtocolTypeEnum.XML_RPC.value,
        ApiProtocolTypeEnum.SOAP.value,
        ApiProtocolTypeEnum.GRAPHQL.value,
        ApiProtocolTypeEnum.DUBBO.value,
        ApiProtocolTypeEnum.THRIFT.value,
    }
    NORMAL_WEBSOCKET_CLOSE_CODES = {None, 1000, 1001}

    @classmethod
    def should_run_api_info_posterior(cls, response: ApiExecutionResponse) -> bool:
        """公共后置只处理标准成功响应，负向响应交给场景断言。"""
        protocol_type = response.request_protocol_type or response.response_mode or ApiProtocolTypeEnum.HTTP.value
        if protocol_type in cls.HTTP_PROTOCOLS or response.code is not None:
            return response.code is not None and 200 <= response.code < 300
        return cls.evaluate(response).success

    @classmethod
    def evaluate(
            cls,
            response: ApiExecutionResponse,
            expected_http_status_codes: list[int] | None = None,
            accept_any_http_status: bool = False,
            display_name: str | None = None,
    ) -> ProtocolCallOutcome:
        protocol_type = response.request_protocol_type or response.response_mode or ApiProtocolTypeEnum.HTTP.value
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            outcome = cls.evaluate_mcp(response)
        elif protocol_type == ApiProtocolTypeEnum.GRPC.value:
            outcome = cls.evaluate_grpc(response)
        elif protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            outcome = cls.evaluate_websocket(response)
        elif protocol_type in cls.HTTP_PROTOCOLS or response.code is not None:
            outcome = cls.evaluate_http_family(
                response,
                protocol_type,
                expected_http_status_codes=expected_http_status_codes,
                accept_any_http_status=accept_any_http_status,
                display_name=display_name,
            )
        else:
            outcome = ProtocolCallOutcome(False, protocol_type, f'接口调用失败：无法识别协议状态（{protocol_type}）')
        if not outcome.success:
            return outcome
        if response.error_msg:
            return ProtocolCallOutcome(False, outcome.protocol_status, response.error_msg)
        return outcome

    @classmethod
    def evaluate_http_family(
            cls,
            response: ApiExecutionResponse,
            protocol_type: str,
            expected_http_status_codes: list[int] | None = None,
            accept_any_http_status: bool = False,
            display_name: str | None = None,
    ) -> ProtocolCallOutcome:
        code = response.code
        protocol_status = cls.http_status(code)
        expected_codes = set(expected_http_status_codes or [])
        status_matched = (
                code is not None
                and (
                        accept_any_http_status
                        or code in expected_codes
                        or (not expected_codes and 200 <= code < 300)
                )
        )
        if not status_matched:
            return ProtocolCallOutcome(
                False,
                protocol_status,
                cls.http_failure_message(response, display_name),
            )

        if protocol_type == ApiProtocolTypeEnum.GRAPHQL.value:
            errors = response.json.get('errors') if isinstance(response.json, dict) else None
            if errors:
                return ProtocolCallOutcome(False, protocol_status,
                                           'GraphQL 接口返回了业务错误，请查看响应中的 errors 了解具体原因。')
        elif protocol_type == ApiProtocolTypeEnum.JSON_RPC.value:
            error = response.json.get('error') if isinstance(response.json, dict) else None
            if error is not None:
                return ProtocolCallOutcome(False, protocol_status,
                                           'JSON-RPC 接口返回了错误，请查看响应中的 error 了解具体原因。')
        elif protocol_type in (ApiProtocolTypeEnum.SOAP.value, ApiProtocolTypeEnum.XML_RPC.value):
            if cls.has_xml_fault(response.text):
                protocol_name = 'SOAP' if protocol_type == ApiProtocolTypeEnum.SOAP.value else 'XML-RPC'
                return ProtocolCallOutcome(False, protocol_status, f'{protocol_name}调用失败：响应包含 Fault')
        return ProtocolCallOutcome(True, protocol_status)

    @classmethod
    def http_failure_message(cls, response: ApiExecutionResponse, display_name: str | None = None) -> str:
        code = response.code
        target = f'接口“{display_name}”' if display_name else '接口'
        if code is None:
            base = f'{target}未收到有效的 HTTP 响应，可能是网络中断、连接超时或服务不可达。'
        else:
            reasons = {
                400: '请求参数或请求体可能不符合接口要求。',
                401: '登录凭证可能无效、已过期，或请求没有携带认证信息。',
                403: '当前账号或凭证可能没有访问权限。',
                404: '请求地址、路径参数或目标资源可能不存在。',
                408: '服务等待请求超时。',
                409: '请求可能与当前数据状态冲突。',
                422: '请求参数未通过服务端校验。',
                429: '请求过于频繁，可能触发了服务限流。',
                500: '服务可能发生内部异常。',
                502: '网关可能无法连接上游服务。',
                503: '服务当前可能不可用或正在维护。',
                504: '网关等待上游服务响应超时。',
            }
            if 300 <= code < 400:
                reason = '请求发生了重定向，尚未得到最终业务响应。'
            elif 400 <= code < 500:
                reason = reasons.get(code, '请求被服务端拒绝，可能需要检查参数、权限或请求格式。')
            elif code >= 500:
                reason = reasons.get(code, '服务或网关可能发生异常。')
            else:
                reason = '返回状态不符合该场景配置的预期。'
            base = f'{target}返回 {cls.http_status(code)}，{reason}'
        detail = cls.response_error_detail(response)
        return f'{base} 服务返回：{detail}' if detail else base

    @staticmethod
    def response_error_detail(response: ApiExecutionResponse) -> str | None:
        value = None
        if isinstance(response.json, dict):
            for key in ('msg', 'message', 'error', 'detail', 'errors'):
                if response.json.get(key) not in (None, '', [], {}):
                    value = response.json.get(key)
                    break
        if value is None and response.error_msg:
            value = response.error_msg
        if value is None and response.text:
            value = response.text
        if value is None:
            return None
        text = str(value).replace('\n', ' ').strip()
        return f'{text[:300]}…' if len(text) > 300 else text

    @staticmethod
    def evaluate_mcp(response: ApiExecutionResponse) -> ProtocolCallOutcome:
        if response.mcp_protocol_error:
            return ProtocolCallOutcome(False, 'MCP protocol error', 'MCP 服务返回协议错误，工具调用没有正常完成。')
        if response.mcp_is_error is True:
            return ProtocolCallOutcome(False, 'MCP isError=true', 'MCP 工具执行失败，请查看工具返回内容中的具体原因。')
        return ProtocolCallOutcome(True, 'MCP success')

    @staticmethod
    def evaluate_grpc(response: ApiExecutionResponse) -> ProtocolCallOutcome:
        status_code = str(response.grpc_status_code or 'UNKNOWN').upper()
        if status_code != 'OK':
            reasons = {
                'UNAUTHENTICATED': '身份凭证可能无效、已过期或缺失。',
                'PERMISSION_DENIED': '当前身份可能没有调用权限。',
                'NOT_FOUND': '请求的服务、方法或资源可能不存在。',
                'INVALID_ARGUMENT': '请求参数可能不符合接口要求。',
                'DEADLINE_EXCEEDED': '调用已超时。',
                'UNAVAILABLE': '服务当前可能不可用。',
                'INTERNAL': '服务可能发生内部异常。',
            }
            reason = reasons.get(status_code, '调用没有正常完成。')
            details = f' 服务返回：{response.grpc_status_details}' if response.grpc_status_details else ''
            return ProtocolCallOutcome(False, f'gRPC {status_code}', f'gRPC 返回 {status_code}，{reason}{details}')
        return ProtocolCallOutcome(True, 'gRPC OK')

    @classmethod
    def evaluate_websocket(cls, response: ApiExecutionResponse) -> ProtocolCallOutcome:
        close_code = response.ws_close_code
        if close_code not in cls.NORMAL_WEBSOCKET_CLOSE_CODES:
            reason = f'：{response.ws_close_reason}' if response.ws_close_reason else ''
            return ProtocolCallOutcome(
                False,
                f'WebSocket {close_code}',
                f'WebSocket调用失败：连接异常关闭（{close_code}）{reason}',
            )
        if response.code not in (101, 1000, 1001, None):
            return ProtocolCallOutcome(
                False,
                f'WebSocket {response.code}',
                f'WebSocket调用失败：协议状态 {response.code}',
            )
        protocol_status = 'WebSocket 101' if response.code == 101 else f'WebSocket {close_code or 1000}'
        return ProtocolCallOutcome(True, protocol_status)

    @classmethod
    def protocol_status(cls, response: ApiExecutionResponse, protocol_type: str) -> str:
        if protocol_type in cls.HTTP_PROTOCOLS:
            return cls.http_status(response.code)
        if protocol_type == ApiProtocolTypeEnum.GRPC.value:
            return f'gRPC {response.grpc_status_code or "UNKNOWN"}'
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            return 'MCP isError=true' if response.mcp_is_error else 'MCP protocol error'
        if protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            return f'WebSocket {response.ws_close_code or response.code or "UNKNOWN"}'
        return protocol_type

    @staticmethod
    def http_status(code: int | None) -> str:
        if code is None:
            return 'UNKNOWN'
        try:
            return f'{code} {HTTPStatus(code).phrase}'
        except ValueError:
            return str(code)

    @staticmethod
    def has_xml_fault(text: str | None) -> bool:
        if not text:
            return False
        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            return False
        return any(element.tag.rsplit('}', 1)[-1].lower() == 'fault' for element in root.iter())
