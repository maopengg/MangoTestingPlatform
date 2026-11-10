# -*- coding: utf-8 -*-
from dataclasses import dataclass
from http import HTTPStatus
from xml.etree import ElementTree

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck as Check
from src.apps.auto_api.exceptions import AutoApiError, MCP_API_CONFIG_INVALID, MCP_API_SCENARIO_INVALID
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.system.services.system_config import (
    API_DEFAULT_ASSERTION_ENABLED_KEY, API_DEFAULT_ASSERTION_CHECKS_KEY, SystemConfigService,
)


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
        # 公共提取只适用于正常响应，不随默认断言开关放行负向响应。
        return cls.evaluate(response, default_checks=frozenset(Check)).success

    @staticmethod
    def default_checks() -> frozenset[Check]:
        if not SystemConfigService.get(API_DEFAULT_ASSERTION_ENABLED_KEY, default=False):
            return frozenset()
        values = SystemConfigService.get(API_DEFAULT_ASSERTION_CHECKS_KEY, default=Check.defaults())
        return frozenset(item for item in Check if item.value in values)

    @staticmethod
    def scenario_checks(expectation: dict) -> frozenset[Check] | None:
        if expectation.get('inherit_system') is not False:
            return None
        return frozenset(item for item in Check if item.value in expectation.get('checks', []))

    @classmethod
    def evaluate(
            cls,
            response: ApiExecutionResponse,
            expected_http_status_codes: list[int] | None = None,
            accept_any_http_status: bool = False,
            display_name: str | None = None,
            expected_mcp_result: str | None = None,
            expected_grpc_status: str | None = None,
            require_http_success: bool = False,
            default_checks: frozenset[Check] | None = None,
    ) -> ProtocolCallOutcome:
        checks = cls.default_checks() if default_checks is None else default_checks
        protocol_type = response.request_protocol_type or response.response_mode or ApiProtocolTypeEnum.HTTP.value
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            expectation = expected_mcp_result or ('success' if Check.MCP_RESULT in checks else 'any')
            outcome = cls.evaluate_mcp(response, expected_result=expectation)
        elif protocol_type == ApiProtocolTypeEnum.GRPC.value:
            expectation = expected_grpc_status or ('OK' if Check.GRPC_STATUS in checks else 'ANY')
            outcome = cls.evaluate_grpc(response, expected_status=expectation)
        elif protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            outcome = cls.evaluate_websocket(response, checks=checks)
        elif protocol_type in cls.HTTP_PROTOCOLS or response.code is not None:
            outcome = cls.evaluate_http_family(
                response,
                protocol_type,
                expected_http_status_codes=expected_http_status_codes,
                accept_any_http_status=accept_any_http_status,
                display_name=display_name,
                checks=checks,
                require_http_success=require_http_success,
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
            checks: frozenset[Check] = frozenset(),
            require_http_success: bool = False,
    ) -> ProtocolCallOutcome:
        code = response.code
        protocol_status = cls.http_status(code)
        expected_codes = set(expected_http_status_codes or [])
        status_matched = (
                code is not None and 100 <= code <= 599
                and (
                        accept_any_http_status
                        or code in expected_codes
                        or (not expected_codes and (
                            not (require_http_success or Check.HTTP_STATUS in checks) or 200 <= code < 300
                        ))
                )
        )
        if not status_matched:
            return ProtocolCallOutcome(
                False,
                protocol_status,
                cls.http_failure_message(response, display_name),
            )

        if protocol_type == ApiProtocolTypeEnum.GRAPHQL.value and Check.GRAPHQL_ERRORS in checks:
            errors = response.json.get('errors') if isinstance(response.json, dict) else None
            if errors:
                return ProtocolCallOutcome(False, protocol_status,
                                           'GraphQL 接口返回了业务错误，请查看响应中的 errors 了解具体原因。')
        elif protocol_type == ApiProtocolTypeEnum.JSON_RPC.value and Check.JSON_RPC_ERROR in checks:
            error = response.json.get('error') if isinstance(response.json, dict) else None
            if error is not None:
                return ProtocolCallOutcome(False, protocol_status,
                                           'JSON-RPC 接口返回了错误，请查看响应中的 error 了解具体原因。')
        elif protocol_type in (ApiProtocolTypeEnum.SOAP.value, ApiProtocolTypeEnum.XML_RPC.value) and Check.XML_FAULT in checks:
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
    def evaluate_mcp(response: ApiExecutionResponse, *, expected_result: str) -> ProtocolCallOutcome:
        if response.mcp_protocol_error:
            return ProtocolCallOutcome(False, 'MCP protocol error', 'MCP 服务返回协议错误，工具调用没有正常完成。')
        if expected_result not in {'success', 'error', 'any'}:
            raise AutoApiError(MCP_API_CONFIG_INVALID, value=(expected_result,))
        if expected_result == 'any':
            return ProtocolCallOutcome(True, 'MCP response received')
        if expected_result == 'error':
            if response.mcp_is_error is True:
                return ProtocolCallOutcome(True, 'MCP expected isError=true')
            return ProtocolCallOutcome(False, 'MCP expected error missing', MCP_API_SCENARIO_INVALID.message)
        if response.mcp_is_error is True:
            return ProtocolCallOutcome(False, 'MCP isError=true', 'MCP 工具执行失败，请查看工具返回内容中的具体原因。')
        return ProtocolCallOutcome(True, 'MCP success')

    @staticmethod
    def evaluate_grpc(response: ApiExecutionResponse, *, expected_status: str) -> ProtocolCallOutcome:
        status_code = str(response.grpc_status_code or 'UNKNOWN').upper()
        expected_status = str(expected_status).upper()
        # 连接不可用、超时、未知结果不能因关闭业务默认断言而误报成功。
        transport_failure = status_code in {'UNAVAILABLE', 'DEADLINE_EXCEEDED', 'UNKNOWN'}
        if transport_failure or (expected_status != 'ANY' and status_code != expected_status):
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
        return ProtocolCallOutcome(True, f'gRPC {status_code}')

    @classmethod
    def evaluate_websocket(cls, response: ApiExecutionResponse, *, checks: frozenset[Check]) -> ProtocolCallOutcome:
        close_code = response.ws_close_code
        if close_code == 1006 or (Check.WEBSOCKET_CLOSE in checks and close_code not in cls.NORMAL_WEBSOCKET_CLOSE_CODES):
            reason = f'：{response.ws_close_reason}' if response.ws_close_reason else ''
            return ProtocolCallOutcome(
                False,
                f'WebSocket {close_code}',
                f'WebSocket调用失败：连接异常关闭（{close_code}）{reason}',
            )
        if Check.WEBSOCKET_HANDSHAKE in checks and response.code not in (101, 1000, 1001, None):
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
