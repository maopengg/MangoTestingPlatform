# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import json

from src.apps.auto_api.schemas.case_schema import (
    scenario_protocol_expectation,
)
from src.apps.auto_api.schemas.execution import (
    ApiExecutionResponse,
)


class ApiTestCaseProtocolMixin:
    @staticmethod
    def has_user_configured_assertions(parameter) -> bool:
        return any((
            getattr(parameter, 'ass_general', None),
            getattr(parameter, 'ass_sql', None),
            getattr(parameter, 'ass_json_all', None),
            getattr(parameter, 'ass_text_all', None),
            getattr(parameter, 'ass_jsonpath', None),
            getattr(parameter, 'ass_schema', None),
        ))

    @classmethod
    def resolve_protocol_expectation(cls, parameter, response: ApiExecutionResponse) -> tuple[list[int], bool]:
        expectation = scenario_protocol_expectation(parameter.body_config)
        mode = str(expectation.get('mode') or '').lower()
        if mode == 'any':
            return [], True
        if mode == 'codes':
            return [int(code) for code in expectation.get('status_codes') or []], False
        if mode == 'success':
            return [], False

        if expectation.get('inherit_system') is False:
            return [], 'http_status' not in expectation.get('checks', [])

        if mode in {'', 'auto'} and cls.has_user_configured_assertions(parameter):
            # 自动模式下，收到有效 HTTP 响应后由用户断言决定业务结果。
            # code=None 等连接级失败不会被 accept_any_http_status 放行。
            return [], True

        # 兼容历史负向场景：旧数据没有协议预期配置时，只在断言明确期待当前 HTTP 状态码时放行。
        response_code = response.code
        if response_code is None:
            return [], False
        expected_codes = cls.infer_legacy_expected_http_codes(parameter)
        if response_code in expected_codes:
            return [response_code], False
        # 历史负向用例可能只断言业务错误码（例如 HTTP 400、业务 code=400001007）。
        # 对已有配置保留这类常见客户端错误；401/403 等鉴权错误仍应直接提示用户。
        has_business_assertion = any((
            parameter.ass_general,
            parameter.ass_json_all,
            parameter.ass_text_all,
            parameter.ass_jsonpath,
            parameter.ass_schema,
        ))
        if has_business_assertion and response_code in {400, 404, 405, 409, 422}:
            return [response_code], False
        return [], False

    @staticmethod
    def infer_legacy_expected_http_codes(parameter) -> set[int]:
        expected_codes: set[int] = set()

        def add_code(value):
            try:
                code = int(value)
            except (TypeError, ValueError):
                return
            if 100 <= code <= 599:
                expected_codes.add(code)

        json_all = parameter.ass_json_all
        if isinstance(json_all, str):
            try:
                json_all = json.loads(json_all)
            except (TypeError, ValueError):
                json_all = None
        if isinstance(json_all, dict):
            add_code(json_all.get('code'))

        for assertion in parameter.ass_jsonpath or []:
            if hasattr(assertion, 'model_dump'):
                assertion = assertion.model_dump()
            if not isinstance(assertion, dict):
                continue
            actual = str(assertion.get('actual') or '').strip()
            method = str(assertion.get('method') or '').lower()
            if actual in {'$.code', '$["code"]', "$['code']"} and ('equal' in method or method == ''):
                add_code(assertion.get('expect'))

        schema = parameter.ass_schema
        if isinstance(schema, dict):
            code_schema = (schema.get('properties') or {}).get('code')
            if isinstance(code_schema, dict):
                add_code(code_schema.get('const'))
        return expected_codes
