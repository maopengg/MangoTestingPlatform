# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-07-04 17:18
# @Author : 毛鹏
import traceback
from contextlib import nullcontext
from urllib.parse import urlparse, urljoin

from mangotools.exceptions import MangoToolsError
from mangotools.data_processor import RegexTool

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.exceptions import (
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_CONFIG_REQUIRED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_CONFIG_EXPRESSION_REQUIRED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_RESPONSE_EXECUTION_FAILED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_RESPONSE_EXPRESSION_NO_MATCH,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CONFIG_PARSE_FAILED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_EXPRESSION_FAILED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_WRITE_FAILED,
    AutoApiError,
    API_POST_JSONPATH_CONFIG_EMPTY,
    API_CUSTOM_FUNCTION_PARSE_FAILED,
    API_POST_FUNCTION_FAILED,
    GRPC_API_API_INFO_BINDING_REQUIRED,
    MCP_API_API_INFO_BINDING_INVALID,
    MCP_API_SERVICE_INVALID,
    MCP_API_TYPE_INVALID,
)
from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_api.services.base.api_base_test_setup.public_base import PublicBase
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService
from src.common.exceptions import MangoServerError
from src.common.logging import log
from src.common.responses.json_response import ensure_jsonpath_source, extract_jsonpath_value


class APIBaseTestSetup(PublicBase):

    def api_request(self,
                    api_info_id,
                    test_env: int,
                    request_model: ApiExecutionRequest = None,
                    api_info: ApiInfo = None,
                    revision_id: int | None = None,
                    release_id: int | None = None,
                    apply_api_info_posterior: bool = True,
                    initialize_public_context: bool = True,
                    preserve_unresolved_cache_placeholders: bool = False,
                    runtime_parameters: dict | None = None,
                    ) -> ApiExecutionResponse:
        api_info = api_info or ApiInfoRuntimeService.resolve_runtime(
            api_info_id,
            revision_id=revision_id,
            release_id=release_id,
        )
        log.api.debug(f'执行API接口-1->ID:{api_info_id},name:{api_info.name}')
        previous_api_info_id = self.current_api_info_id
        self.current_api_info_id = api_info.id
        try:
            self.init_test_object(api_info.project_product_id, test_env)
            if initialize_public_context:
                self.init_public(api_info.project_product_id, test_env)
        finally:
            self.current_api_info_id = previous_api_info_id
        # 本次填写值优先于公共变量初始化结果，且不写回公共变量。
        for key, value in (runtime_parameters or {}).items():
            self.test_data.set_cache(key, value)
        # API info的请求
        if request_model is None:
            if getattr(api_info, 'headers', None) is not None:
                headers = api_info.headers
            else:
                headers = self.init_headers(api_info.project_product_id)
            mcp_binding = self._resolve_mcp_binding(api_info)
            grpc_binding = self._resolve_grpc_binding(api_info)
            request_model = ApiExecutionRequest(
                method=MethodEnum(api_info.method).name,
                url=api_info.url,
                headers=headers,
                params=getattr(api_info, 'params', None),
                protocol_type=api_info.protocol_type,
                body_type=getattr(api_info, 'body_type', ApiBodyTypeEnum.NONE.value),
                body_config=getattr(api_info, 'body_config', None),
                sse_config=getattr(api_info, 'sse_config', None),
                posterior_file=None,
                mcp_server_id=(mcp_binding or {}).get('server_id'),
                mcp_tool_id=(mcp_binding or {}).get('tool_id'),
                mcp_tool_name=(mcp_binding or {}).get('tool_name'),
                mcp_config={
                    **((mcp_binding or {}).get('mcp_config') or {}),
                    'transport_type': (mcp_binding or {}).get('transport_type'),
                    'input_schema': (mcp_binding or {}).get('input_schema'),
                    'output_schema': (mcp_binding or {}).get('output_schema'),
                    'schema_hash': (mcp_binding or {}).get('schema_hash'),
                } if mcp_binding else None,
                grpc_service_id=(grpc_binding or {}).get('service_id'),
                grpc_method_id=(grpc_binding or {}).get('method_id'),
                grpc_full_method=(grpc_binding or {}).get('full_method'),
                grpc_request_message=(grpc_binding or {}).get('request_message'),
                grpc_response_message=(grpc_binding or {}).get('response_message'),
                grpc_config={
                    **((grpc_binding or {}).get('grpc_config') or {}),
                    'descriptor_file_path': (grpc_binding or {}).get('descriptor_file_path'),
                    'tls_enabled': (grpc_binding or {}).get('tls_enabled'),
                    'client_streaming': (grpc_binding or {}).get('client_streaming'),
                    'server_streaming': (grpc_binding or {}).get('server_streaming'),
                    'request_json_schema': (grpc_binding or {}).get('request_json_schema'),
                    'response_json_schema': (grpc_binding or {}).get('response_json_schema'),
                } if grpc_binding else None,
            )
        else:
            self._apply_mcp_binding(api_info, request_model)
            self._apply_grpc_binding(api_info, request_model)
        replacement_context = (
            self.test_data.preserve_unresolved_cache_placeholders()
            if preserve_unresolved_cache_placeholders
            else nullcontext()
        )
        with replacement_context:
            previous_resource_api = getattr(self, 'resource_cleanup_api_info_id', None)
            previous_resource_env = getattr(self, 'resource_cleanup_test_env', None)
            self.resource_cleanup_api_info_id, self.resource_cleanup_test_env = api_info.id, test_env
            try:
                response = self.http(self.request_data_clean(request_model), api_info.project_product_id)
            finally:
                self.resource_cleanup_api_info_id, self.resource_cleanup_test_env = previous_resource_api, previous_resource_env
        if not apply_api_info_posterior:
            response.api_info_posterior_skipped_reason = (
                '场景已配置断言，本次由场景断言判定结果，未执行 API Info 公共后置处理'
            )
            return response
        if not ProtocolCallOutcomeService.should_run_api_info_posterior(response):
            response.api_info_posterior_skipped_reason = (
                '接口未返回标准成功状态，已跳过仅适用于成功响应的 API Info 公共后置处理'
            )
            return response
        try:
            if api_info.posterior_re:
                self.api_info_posterior_json_re(api_info.posterior_re, response)
            if api_info.posterior_json_path:
                self.api_info_posterior_json_path(api_info.posterior_json_path, response)
            if api_info.posterior_func:
                self.execute_analytic_func(api_info.posterior_func, self, response, error_msg=API_POST_FUNCTION_FAILED)
            return response
        except (MangoServerError, MangoToolsError) as error:
            response.error_msg = error.msg
            return response

    @staticmethod
    def _resolve_mcp_binding(api_info: ApiInfo) -> dict | None:
        if api_info.protocol_type != ApiProtocolTypeEnum.MCP.value:
            return None
        snapshot = getattr(api_info, '_mcp_binding_snapshot', None)
        if isinstance(snapshot, dict):
            return snapshot
        binding = ApiInfoRuntimeService.capture_mcp_binding(api_info)
        if not binding:
            raise AutoApiError(MCP_API_API_INFO_BINDING_INVALID)
        if binding.get('tool_type') != 'tool':
            raise AutoApiError(MCP_API_TYPE_INVALID, value=(binding.get('tool_type'),))
        if binding.get('tool_enabled') is False:
            raise AutoApiError(MCP_API_SERVICE_INVALID, value=(binding.get('tool_name') or '-',))
        return binding

    @staticmethod
    def _resolve_grpc_binding(api_info: ApiInfo) -> dict | None:
        if api_info.protocol_type != ApiProtocolTypeEnum.GRPC.value:
            return None
        snapshot = getattr(api_info, '_grpc_binding_snapshot', None)
        if isinstance(snapshot, dict):
            return snapshot
        binding = ApiInfoRuntimeService.capture_grpc_binding(api_info)
        if not binding:
            raise AutoApiError(GRPC_API_API_INFO_BINDING_REQUIRED)
        return binding

    @classmethod
    def _apply_mcp_binding(cls, api_info: ApiInfo, request_model: ApiExecutionRequest) -> ApiExecutionRequest:
        mcp_binding = cls._resolve_mcp_binding(api_info)
        if not mcp_binding:
            return request_model
        request_model.mcp_server_id = mcp_binding.get('server_id')
        request_model.mcp_tool_id = mcp_binding.get('tool_id')
        request_model.mcp_tool_name = mcp_binding.get('tool_name')
        request_model.mcp_config = {
            **(mcp_binding.get('mcp_config') or {}),
            **(request_model.mcp_config or {}),
            'transport_type': mcp_binding.get('transport_type'),
            'input_schema': mcp_binding.get('input_schema'),
            'output_schema': mcp_binding.get('output_schema'),
            'schema_hash': mcp_binding.get('schema_hash'),
            'risk_level': mcp_binding.get('risk_level'),
            'write_operation': mcp_binding.get('write_operation'),
            'require_confirm': mcp_binding.get('require_confirm'),
        }
        return request_model

    @classmethod
    def _apply_grpc_binding(cls, api_info: ApiInfo, request_model: ApiExecutionRequest) -> ApiExecutionRequest:
        grpc_binding = cls._resolve_grpc_binding(api_info)
        if not grpc_binding:
            return request_model
        request_model.grpc_service_id = grpc_binding.get('service_id')
        request_model.grpc_method_id = grpc_binding.get('method_id')
        request_model.grpc_full_method = grpc_binding.get('full_method')
        request_model.grpc_request_message = grpc_binding.get('request_message')
        request_model.grpc_response_message = grpc_binding.get('response_message')
        request_model.grpc_config = {
            **(grpc_binding.get('grpc_config') or {}),
            **(request_model.grpc_config or {}),
            'descriptor_file_path': grpc_binding.get('descriptor_file_path'),
            'tls_enabled': grpc_binding.get('tls_enabled'),
            'client_streaming': grpc_binding.get('client_streaming'),
            'server_streaming': grpc_binding.get('server_streaming'),
            'request_json_schema': grpc_binding.get('request_json_schema'),
            'response_json_schema': grpc_binding.get('response_json_schema'),
        }
        return request_model

    def request_data_clean(self, request_data_model: ApiExecutionRequest) -> ApiExecutionRequest:
        self.ensure_execution_context()
        target_address = self.test_data.get_cache('url')
        log.api.debug(f'清洗请求数据-1->{request_data_model.model_dump_json()}')
        try:
            for key, value in request_data_model:
                if key == 'headers':
                    value = self.test_data.replace(value)
                    if value and isinstance(value, str):
                        value = self.test_data.loads(value) if value else value
                    setattr(request_data_model, key, value)
                elif key in {
                    'body_config',
                    'sse_config',
                    'mcp_config',
                    'grpc_config',
                    'request_body',
                    'request_files',
                    'request_content_type',
                    'trace_parent_step_id',
                }:
                    continue
                else:
                    value = self.test_data.replace(value)
                    setattr(request_data_model, key, value)
            result = urlparse(request_data_model.url)
            if not all([result.scheme, result.netloc]):
                request_data_model.url = urljoin(target_address, request_data_model.url)
        except MangoToolsError as error:
            traceback.print_exc()
            raise
        log.api.debug(f'清洗请求数据-2->{request_data_model}')
        return request_data_model

    def api_info_posterior_json_path(self, posterior_json_path: list[dict], response: ApiExecutionResponse):
        log.api.debug(f'执行API接口-4->后置jsonpath:{posterior_json_path}')
        ensure_jsonpath_source(response.json)
        for i in posterior_json_path:
            key: str = self.test_data.replace(i.get('key'))
            value: str = self.test_data.replace(i.get('value'))
            if not key or not value:
                raise AutoApiError(API_POST_JSONPATH_CONFIG_EMPTY)
            if key and key.startswith('$.'):
                key_expression = key
                key = extract_jsonpath_value(
                    response.json,
                    key_expression,
                    operation='API信息后置JSONPath缓存Key提取',
                )
            extracted_value = extract_jsonpath_value(
                response.json,
                value,
                operation='API信息后置JSONPath提取',
                cache_key=key,
            )
            self.test_data.set_cache(key, extracted_value)

    def api_info_posterior_json_re(
            self,
            posterior_re,
            response: ApiExecutionResponse,
            operation: str = 'API信息后置正则提取',
    ):
        log.api.debug(f'执行API接口-3->后置正则:{posterior_re}')
        for index, i in enumerate(posterior_re, start=1):
            try:
                key: str = self.test_data.replace(i.get('key'))
                value: str = self.test_data.replace(i.get('value'))
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CONFIG_PARSE_FAILED,
                                   value=(operation, index, error.msg)) from error
            if not key:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_CONFIG_REQUIRED, value=(operation, index))
            if not value:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_CONFIG_EXPRESSION_REQUIRED,
                                   value=(operation, index, key))
            if response.text is None:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_RESPONSE_EXECUTION_FAILED,
                                   value=(operation, index, key))
            try:
                match = RegexTool.search(response.text, value)
            except MangoToolsError as error:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_REGEX_EXPRESSION_FAILED,
                                   value=(operation, index, key, value, error.msg)) from error
            if match is None:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_RESPONSE_EXPRESSION_NO_MATCH,
                                   value=(operation, index, key, value, len(response.text)))
            try:
                self.test_data.set_cache(key, RegexTool.extracted_value(match))
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_CACHE_WRITE_FAILED,
                                   value=(operation, index, key, error.msg)) from error

    def analytic_func(self, func_str, func_name='func'):
        func_str = self.test_data.replace(func_str)
        log.api.debug(f'执行API接口-5->后置函数:{func_str}')
        try:
            global_namespace = {}
            exec(func_str, global_namespace)
            func = global_namespace.get(func_name)
            if not callable(func):
                raise AutoApiError(API_CUSTOM_FUNCTION_PARSE_FAILED, value=(f'未定义可调用的 {func_name}(...) 函数',))
            return func
        except AutoApiError:
            raise
        except SyntaxError as error:
            detail = f'第{error.lineno or "未知"}行语法错误：{error.msg}'
            raise AutoApiError(API_CUSTOM_FUNCTION_PARSE_FAILED, value=(detail,)) from error
        except Exception as error:
            log.api.warning(f'函数字符串：{func_str}')
            log.api.error(
                f'自定义函数执行失败，函数字符串：{func_str}，失败类型：{error}，失败明细：{traceback.format_exc()}')
            detail = f'{type(error).__name__}: {str(error) or "未提供错误信息"}'
            raise AutoApiError(API_CUSTOM_FUNCTION_PARSE_FAILED, value=(detail,)) from error

    def execute_analytic_func(self, func_str, *args, error_msg=API_CUSTOM_FUNCTION_PARSE_FAILED):
        try:
            return self.analytic_func(func_str)(*args)
        except MangoServerError as error:
            raise AutoApiError(error_msg, value=(error.msg,)) from error
        except MangoToolsError as error:
            raise AutoApiError(error_msg, value=(error.msg,)) from error
        except Exception as error:
            log.api.error(
                f'自定义函数执行失败，函数字符串：{func_str}，失败类型：{error}，失败明细：{traceback.format_exc()}')
            detail = f'{type(error).__name__}: {str(error) or "未提供错误信息"}'
            raise AutoApiError(error_msg, value=(detail,)) from error
