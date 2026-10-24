from types import SimpleNamespace
from unittest import TestCase

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService
from src.apps.auto_api.services.test_case.test_api_info import TestApiInfo


def response(**kwargs) -> ApiExecutionResponse:
    defaults = {
        'code': 200,
        'time': 0.1,
        'url': 'https://example.com/api',
        'headers': {},
        'response_mode': ApiProtocolTypeEnum.HTTP.value,
        'request_protocol_type': ApiProtocolTypeEnum.HTTP.value,
    }
    defaults.update(kwargs)
    return ApiExecutionResponse(**defaults)


class ProtocolCallOutcomeServiceTest(TestCase):
    def test_http_accepts_all_2xx_and_rejects_3xx_or_above(self):
        for code in (200, 201, 204, 206):
            with self.subTest(code=code):
                self.assertTrue(ProtocolCallOutcomeService.evaluate(response(code=code)).success)
        for code in (300, 400, 500):
            with self.subTest(code=code):
                outcome = ProtocolCallOutcomeService.evaluate(response(code=code))
                self.assertFalse(outcome.success)
                self.assertIn(str(code), outcome.error_message)

    def test_sse_uses_http_handshake_status(self):
        outcome = ProtocolCallOutcomeService.evaluate(response(
            code=503,
            response_mode=ApiProtocolTypeEnum.SSE.value,
            request_protocol_type=ApiProtocolTypeEnum.SSE.value,
        ))
        self.assertFalse(outcome.success)

    def test_expected_negative_http_status_is_accepted(self):
        outcome = ProtocolCallOutcomeService.evaluate(
            response(code=422),
            expected_http_status_codes=[400, 422],
        )
        self.assertTrue(outcome.success)

    def test_api_info_posterior_only_runs_for_standard_success_response(self):
        self.assertTrue(ProtocolCallOutcomeService.should_run_api_info_posterior(response(code=200)))
        self.assertFalse(ProtocolCallOutcomeService.should_run_api_info_posterior(response(code=403)))
        self.assertFalse(ProtocolCallOutcomeService.should_run_api_info_posterior(response(code=500)))

    def test_http_failure_message_explains_status_in_plain_language(self):
        unauthorized = ProtocolCallOutcomeService.evaluate(
            response(code=401, json={'message': 'token expired'}),
            display_name='员工登录',
        )
        server_error = ProtocolCallOutcomeService.evaluate(
            response(code=500),
            display_name='查询订单',
        )
        self.assertIn('接口“员工登录”返回 401 Unauthorized', unauthorized.error_message)
        self.assertIn('登录凭证可能无效', unauthorized.error_message)
        self.assertIn('token expired', unauthorized.error_message)
        self.assertIn('接口“查询订单”返回 500 Internal Server Error', server_error.error_message)
        self.assertIn('服务可能发生内部异常', server_error.error_message)

    def test_protocol_failure_has_priority_over_post_process_failure(self):
        outcome = ProtocolCallOutcomeService.evaluate(response(
            code=500,
            error_msg='响应提取失败',
        ))
        self.assertFalse(outcome.success)
        self.assertIn('500', outcome.error_message)

    def test_graphql_and_json_rpc_protocol_errors_fail(self):
        graphql = ProtocolCallOutcomeService.evaluate(response(
            request_protocol_type=ApiProtocolTypeEnum.GRAPHQL.value,
            response_mode=ApiProtocolTypeEnum.GRAPHQL.value,
            json={'errors': [{'message': 'invalid'}]},
        ))
        json_rpc = ProtocolCallOutcomeService.evaluate(response(
            request_protocol_type=ApiProtocolTypeEnum.JSON_RPC.value,
            response_mode=ApiProtocolTypeEnum.JSON_RPC.value,
            json={'jsonrpc': '2.0', 'error': {'code': -32600}},
        ))
        self.assertFalse(graphql.success)
        self.assertFalse(json_rpc.success)

    def test_grpc_mcp_and_websocket_use_native_status(self):
        grpc_outcome = ProtocolCallOutcomeService.evaluate(response(
            code=None,
            request_protocol_type=ApiProtocolTypeEnum.GRPC.value,
            response_mode=ApiProtocolTypeEnum.GRPC.value,
            grpc_status_code='NOT_FOUND',
        ))
        mcp_outcome = ProtocolCallOutcomeService.evaluate(response(
            code=None,
            request_protocol_type=ApiProtocolTypeEnum.MCP.value,
            response_mode=ApiProtocolTypeEnum.MCP.value,
            mcp_is_error=True,
        ))
        websocket_outcome = ProtocolCallOutcomeService.evaluate(response(
            code=1006,
            request_protocol_type=ApiProtocolTypeEnum.WEBSOCKET.value,
            response_mode=ApiProtocolTypeEnum.WEBSOCKET.value,
            ws_close_code=1006,
        ))
        self.assertFalse(grpc_outcome.success)
        self.assertFalse(mcp_outcome.success)
        self.assertFalse(websocket_outcome.success)

        self.assertTrue(ProtocolCallOutcomeService.evaluate(response(
            code=None,
            request_protocol_type=ApiProtocolTypeEnum.GRPC.value,
            response_mode=ApiProtocolTypeEnum.GRPC.value,
            grpc_status_code='OK',
        )).success)
        self.assertTrue(ProtocolCallOutcomeService.evaluate(response(
            code=None,
            request_protocol_type=ApiProtocolTypeEnum.MCP.value,
            response_mode=ApiProtocolTypeEnum.MCP.value,
            mcp_is_error=False,
        )).success)
        self.assertTrue(ProtocolCallOutcomeService.evaluate(response(
            code=101,
            request_protocol_type=ApiProtocolTypeEnum.WEBSOCKET.value,
            response_mode=ApiProtocolTypeEnum.WEBSOCKET.value,
        )).success)

    def test_api_info_result_contains_explicit_call_status(self):
        setup = SimpleNamespace(test_data=SimpleNamespace(get_all=lambda: {}))
        test_api_info = TestApiInfo.__new__(TestApiInfo)
        test_api_info.test_setup = setup
        result = test_api_info.save_api_info(SimpleNamespace(name='demo'), response(code=400))
        self.assertEqual(result['status'], StatusEnum.FAIL.value)
        self.assertFalse(result['call_success'])
        self.assertIn('400', result['error_msg'])
