# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json
import os
import re
import traceback

import jsonschema
import requests
import time
from django.conf import settings
from jsonschema import validate
from mangotools.enums import StatusEnum
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.exceptions import (
    AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_OUT_OF_RANGE,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_CONFIG_EXPRESSION_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_RESPONSE_ASSERTION_TYPE_CONFIG_NOT_FOUND,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED_CODE_ASSERTION_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_RESULT_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_NOT_FOUND,
    AUTO_API_BASE_CASE_PARAMETER_JSON_ASSERTION_CONFIG_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID_CODE_TIME_CONFIG_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_PLAN_EXECUTION_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_SQL_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_JSONPATH_JSON_RESPONSE_CONFIG_REQUIRED,
    AUTO_API_BASE_CASE_PARAMETER_REGEX_RESPONSE_ASSERTION_CONFIG_EXPRESSION_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED_CODE_ASSERTION_CONFIG_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_SQL_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED_CODE_SQL_DATABASE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_DATABASE_RESULT_WRITE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_CONFIG_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_RESULT_EXPRESSION_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_WRITE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_EXPRESSION_PARSE_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_NOT_FOUND,
    AUTO_API_BASE_CASE_PARAMETER_SQL_ASSERTION_CONFIG_INVALID,
    AUTO_API_BASE_CASE_PARAMETER_JSONPATH_JSON_FAILED,
    AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_FAILED,
    AUTO_API_DYNAMIC_ERROR,
    AutoApiError,
    API_ASSERTION_FAILED,
    API_DOWNLOAD_FAILED,
    API_CASE_PRE_SQL_EMPTY,
    API_CASE_PRE_FUNCTION_FAILED,
    API_CASE_POST_FUNCTION_FAILED,
    GRPC_API_STATUS_INVALID,
    MCP_API_INVALID,
    MCP_API_CONFIG_INVALID,
    MCP_API_SCENARIO_INVALID,
)
from src.apps.auto_api.schemas.case_schema import scenario_grpc_config, scenario_mcp_config
from src.apps.auto_api.schemas.execution import ApiExecutionResponse, ApiExecutionRequest, ApiAssertionResult
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.assertion_diagnostics import (
    describe_json_consistency,
    describe_schema_config,
    describe_schema_validation,
    first_text_difference,
    sql_preview,
    typed_value,
    value_preview,
)
from src.apps.auto_api.services.base.data_source_operation import (
    cache_data_source_result,
    execute_data_source_operation,
)
from src.apps.auto_api.services.base.sql_environment import should_execute_sql
from src.common.exceptions import ErrorDefinition, MangoServerError
from src.common.logging import log
from src.common.responses.json_response import (
    ensure_jsonpath_source,
    extract_jsonpath_value,
    improve_jsonpath_error_message,
    is_jsonpath_source,
    json_value_type,
)
from src.common.testing import ObtainAssertion
from ...models import ApiCaseDetailedParameter, ApiHeaders, ApiInfo


class CaseParameter:
    """ 测试用例详情的前后置+断言+缓存 """

    def __init__(
            self,
            api_base_test_setup: APIBaseTestSetup,
            parameter: ApiCaseDetailedParameter,
            api_info: ApiInfo,
            test_env: int,
    ):
        self.test_setup = api_base_test_setup
        self.parameter = parameter
        self.api_info = api_info
        self.test_env = test_env
        self.ass_result: list[ApiAssertionResult] = []

        self.test_data = api_base_test_setup.test_data
        self.test_object = api_base_test_setup.test_object

    def headers(self, parameter: ApiCaseDetailedParameter, headers: dict) -> dict:
        if hasattr(parameter, '_revision_headers'):
            revision_headers = parameter._revision_headers
            return headers if revision_headers is None else dict(revision_headers)
        if parameter.headers:
            case_details_header = {}
            for i in ApiHeaders.objects.filter(id__in=parameter.headers):
                case_details_header[i.key] = i.value
            return case_details_header
        else:
            return headers

    def front_main(self, request: ApiExecutionRequest) -> ApiExecutionRequest:
        if self.parameter.front_sql:
            self.__front_sql(self.parameter.front_sql)
        if self.parameter.front_func:
            request = self.__front_func(self.parameter.front_func, request)
        return request

    def ass_main(self, response: ApiExecutionResponse, ) -> tuple[list[ApiAssertionResult], int, str | None]:
        return self.verify_all_assertions(response)

    def __ass_mcp_default(self, response: ApiExecutionResponse):
        if response.response_mode != 'mcp':
            return
        mcp_config = scenario_mcp_config(self.parameter.body_config)
        expected_result = mcp_config.get('expected_result') or 'success'
        if expected_result not in {'success', 'error', 'any'}:
            raise AutoApiError(MCP_API_CONFIG_INVALID, value=(expected_result,))
        if expected_result == 'any':
            return
        is_error = bool(response.mcp_is_error)
        if expected_result == 'success' and is_error:
            message = response.text or response.mcp_content or response.mcp_structured_content or response.mcp_meta or 'MCP Tool返回业务错误'
            raise AutoApiError(MCP_API_INVALID, value=(response.mcp_tool_name or '-', value_preview(message),))
        if expected_result == 'error' and not is_error:
            raise AutoApiError(MCP_API_SCENARIO_INVALID)

    def __ass_grpc_default(self, response: ApiExecutionResponse):
        if response.response_mode != 'grpc':
            return
        grpc_config = scenario_grpc_config(self.parameter.body_config)
        expected_status = str(grpc_config.get('expected_status') or 'OK').upper()
        if expected_status == 'ANY':
            return
        actual_status = str(response.grpc_status_code or 'UNKNOWN').upper()
        if actual_status != expected_status:
            raise AutoApiError(GRPC_API_STATUS_INVALID,
                               value=(
                                   response.grpc_full_method or '-',
                                   actual_status,
                                   expected_status,
                                   response.grpc_status_details or '-',
                               ),
                               )

    def verify_all_assertions(self, response: ApiExecutionResponse) -> tuple[list[ApiAssertionResult], int, str | None]:
        self.ass_result = []
        assertion_tasks = [
            ('MCP默认断言', 'mcp_default', lambda: self.__ass_mcp_default(response)),
            ('gRPC默认断言', 'grpc_default', lambda: self.__ass_grpc_default(response)),
            (
                '响应字段断言',
                'jsonpath',
                lambda: self.__ass_jsonpath(
                    response,
                    self.parameter.ass_jsonpath,
                    continue_on_failure=True,
                ) if self.parameter.ass_jsonpath else None,
            ),
            (
                'SQL断言',
                'sql',
                lambda: self.__ass_sql(self.parameter.ass_sql, continue_on_failure=True)
                if getattr(self.parameter, 'ass_sql', None) else None,
            ),
            (
                '通用断言',
                'general',
                lambda: self.__ass_general(
                    self.parameter.ass_general,
                    self.parameter.ass_general,
                    continue_on_failure=True,
                ) if self.parameter.ass_general else None,
            ),
            ('JSON一致断言', 'json_all', lambda: self.__verify_json_all(response)),
            ('文本一致断言', 'text_all', lambda: self.__verify_text_all(response)),
            ('结构化断言', 'schema', lambda: self.__ass_schema(response)),
        ]

        failure_messages = []
        for title, source_type, assertion_task in assertion_tasks:
            result_count = len(self.ass_result)
            try:
                assertion_task()
            except (AutoApiError, AutoApiError, MangoToolsError) as error:
                failure_messages.append(error.msg)
                if len(self.ass_result) == result_count:
                    self.__append_assertion_error(title, source_type, error.msg)
            except Exception as error:
                error_message = f'API断言发生未知错误，管理员请检查：{error}'
                log.api.error(f'{error_message}，{traceback.format_exc()}')
                failure_messages.append(error_message)
                if len(self.ass_result) == result_count:
                    self.__append_assertion_error(title, source_type, error_message)

        if failure_messages:
            return self.ass_result, StatusEnum.FAIL.value, '；'.join(failure_messages)
        return self.ass_result, StatusEnum.SUCCESS.value, None

    def __verify_json_all(self, response: ApiExecutionResponse):
        if not self.parameter.ass_json_all:
            return
        try:
            expect = self.test_setup.test_data.replace(self.parameter.ass_json_all)
        except (MangoServerError, MangoToolsError) as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_JSON_ASSERTION_CONFIG_PARSE_FAILED,
                               value=(error.msg,)) from error
        self.__ass_json_all(response.json, expect)

    def __verify_text_all(self, response: ApiExecutionResponse):
        if not self.parameter.ass_text_all:
            return
        try:
            expect = self.test_setup.test_data.replace(self.parameter.ass_text_all)
        except (MangoServerError, MangoToolsError) as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED,
                               value=(error.msg,)) from error
        self.__ass_test_all(response.text, expect)

    def __append_assertion_error(
            self,
            title: str,
            source_type: str,
            error_message: str,
            raw_config=None,
            group_name: str | None = None,
            group_logic: str | None = None,
            assertion_index: int | None = None,
    ):
        display_error_message = improve_jsonpath_error_message(error_message) \
            if source_type == 'jsonpath' else error_message
        self.ass_result.append(ApiAssertionResult(
            method=title,
            status=StatusEnum.FAIL.value,
            ass_msg=display_error_message,
            source_type=source_type,
            raw_config=raw_config,
            group_name=group_name,
            group_logic=group_logic,
            assertion_index=assertion_index,
        ))

    def posterior_main(self, response: ApiExecutionResponse) -> ApiExecutionResponse:
        if self.parameter.posterior_response:
            self.__posterior_response(
                response.json,
                self.parameter.posterior_response,
            )
        if self.parameter.posterior_response_text:
            self.__posterior_response_text(
                response,
                self.parameter.posterior_response_text,
            )
        if self.parameter.posterior_sql:
            self.__posterior_sql(self.parameter.posterior_sql)
        if self.parameter.posterior_sleep is not None:
            self.__posterior_sleep(self.parameter.posterior_sleep)
        if self.parameter.posterior_func:
            response = self.__posterior_func(self.parameter.posterior_func, response)
        if self.parameter.posterior_file:
            self.__posterior_file(self.parameter.posterior_file)
        return response

    def __posterior_func(self, posterior_func: str, response: ApiExecutionResponse) -> ApiExecutionRequest:
        log.api.debug(f'用例详情后置-3->函数：{posterior_func}')
        return self.test_setup.execute_analytic_func(
            posterior_func,
            self,
            response,
            error_msg=API_CASE_POST_FUNCTION_FAILED,
        )

    @staticmethod
    def __posterior_sleep(value):
        if isinstance(value, bool):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID, value=(value,))
        try:
            seconds = int(value)
        except (TypeError, ValueError) as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_INVALID_CODE_TIME_CONFIG_INVALID,
                               value=(value,)) from error
        if seconds < 0 or seconds > 32767:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_TIME_CONFIG_OUT_OF_RANGE, value=(seconds,))
        try:
            time.sleep(seconds)
        except Exception as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_PLAN_EXECUTION_FAILED, value=(seconds, error)) from error

    def __posterior_sql(self, sql_list: list[dict]):
        for index, sql_obj in enumerate(sql_list, start=1):
            if not should_execute_sql(sql_obj, self.test_env):
                log.api.info(
                    f'用例场景后置SQL跳过执行，当前环境：{self.test_env}，配置环境：{sql_obj.get("test_envs")}'
                )
                continue
            datasource_alias = sql_obj.get('datasource_alias')
            if not datasource_alias:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_CONFIG_REQUIRED, value=(index,))
            try:
                key = self.test_setup.test_data.replace(sql_obj.get('key'))
                value = self.test_setup.test_data.replace(sql_obj.get('value'))
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_FAILED, value=(index, error.msg)) from error
            log.api.debug(f'用例详情后置sql-1->key:{key}，value:{value}')
            if not value:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_CONFIG_REQUIRED, value=(index,))
            try:
                res = execute_data_source_operation(
                    self.test_setup,
                    self.test_env,
                    sql_obj,
                    source_context=self.__sql_source_context('parameter_posterior', index),
                )
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED,
                                   value=(index, datasource_alias, error.msg, sql_preview(value))) from error
            except Exception as error:
                log.api.error(f'后置SQL执行异常：{traceback.format_exc()}')
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_DATABASE_FAILED_CODE_SQL_DATABASE_FAILED,
                                   value=(index, datasource_alias, error, sql_preview(value))) from error
            log.api.debug(f'用例详情后置sql-2->key：{key}，sql：{value}，结果：{res}')
            if key:
                if not cache_data_source_result(self.test_setup, key, res):
                    raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_DATABASE_RESULT_WRITE_FAILED,
                                       value=(index, key))

    def __posterior_response(self, response_dict: dict, posterior_response: list[dict]):
        try:
            ensure_jsonpath_source(response_dict)
        except AutoApiError as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_FAILED, value=(error.msg,)) from error
        for index, i in enumerate(posterior_response, start=1):
            try:
                key: str = self.test_setup.test_data.replace(i.get('key'))
                value: str = self.test_setup.test_data.replace(i.get('value'))
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_JSON_RESPONSE_CONFIG_PARSE_FAILED,
                                   value=(index, error.msg)) from error
            if not key:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_CONFIG_REQUIRED, value=(index,))
            if not value:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_JSONPATH_JSON_RESPONSE_CONFIG_REQUIRED,
                                   value=(index, key))
            if key and key.startswith('$.'):
                key_expression = key
                key = extract_jsonpath_value(
                    response_dict,
                    key_expression,
                    operation=f'响应JSON缓存Key提取（第{index}项）',
                )
                if not isinstance(key, str) or not key.strip():
                    raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_RESULT_EXPRESSION_FAILED,
                                       value=(index, key_expression, typed_value(key)))
            value = extract_jsonpath_value(
                response_dict,
                value,
                operation=f'响应JSON提取（第{index}项）',
                cache_key=key,
            )
            log.api.debug(f'用例详情后置-1->key：{i["value"]}，value：{value}')
            try:
                self.test_setup.test_data.set_cache(key, value)
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_JSON_RESPONSE_WRITE_FAILED,
                                   value=(index, key, error.msg)) from error

    def __posterior_response_text(self, response: ApiExecutionResponse, posterior_response: list[dict]):
        self.test_setup.api_info_posterior_json_re(
            posterior_response,
            response,
            operation='响应文本提取',
        )

    def __posterior_file(self, posterior_file: list[dict]):
        for i in posterior_file:
            url_path = i.get('value')
            if not url_path:
                continue
            try:
                filename = os.path.basename(url_path.split("?")[0])
                local_file_path = os.path.join(settings.DOWNLOAD_DIR, filename)
                response = requests.get(url_path, stream=True, timeout=30, proxies={'http': None, 'https': None})
                response.raise_for_status()
                with open(local_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.test_setup.test_data.set_cache(i.get('key'), local_file_path)
            except Exception as e:
                log.api.error(f'下载文件异常：{traceback.format_exc()}')
                raise AutoApiError(API_DOWNLOAD_FAILED, value=(e,))

    def __ass_jsonpath(
            self,
            response: ApiExecutionResponse,
            ass_jsonpath,
            continue_on_failure: bool = False,
    ):
        if ass_jsonpath:
            self.__run_group_assertions(
                ass_jsonpath,
                lambda i, raw_i, index: self.__build_response_extract_ass_dict(response, i, raw_i, index),
                default_source_type='jsonpath',
                continue_on_failure=continue_on_failure,
            )

    @staticmethod
    def __extract_regex_assertion_value(response_text: str | None, expression: str, index: int):
        try:
            pattern = re.compile(expression)
        except (re.error, TypeError) as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_REGEX_RESPONSE_ASSERTION_CONFIG_EXPRESSION_INVALID,
                               value=(index, expression, error)) from error
        if response_text is None:
            return None, '当前响应没有文本内容'
        match = pattern.search(response_text)
        if match is None:
            return None, f'正则未匹配响应文本（响应长度：{len(response_text)}）'
        groups = match.groups()
        if not groups:
            return match.group(0), '已提取完整匹配内容'
        if len(groups) == 1:
            return groups[0], '已提取第1个捕获组'
        return list(groups), f'已提取{len(groups)}个捕获组'

    def __build_response_extract_ass_dict(
            self,
            response: ApiExecutionResponse,
            i: dict,
            raw_i: dict | None = None,
            index: int = 1,
    ):
        assertion_type = str(i.get('assertion_type') or 'jsonpath').lower()
        assertion_titles = {
            'jsonpath': 'JSONPath提取断言',
            'regex': '正则提取断言',
            'cache': '缓存值断言',
        }
        assertion_title = assertion_titles.get(assertion_type, '响应提取断言')
        raw_expression = i.get('actual')
        if assertion_type == 'cache' and not re.fullmatch(r'\$\{\{[^{}]+\}\}', str(raw_expression or '').strip()):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_CONFIG_EXPRESSION_INVALID, value=(index,))
        if assertion_type not in {'jsonpath', 'regex', 'cache'}:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_RESPONSE_ASSERTION_TYPE_CONFIG_NOT_FOUND,
                               value=(index, assertion_type))
        if not i.get('method'):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED, value=(assertion_title, index))
        try:
            expect = self.test_setup.test_data.replace(i.get('expect'))
        except (MangoServerError, MangoToolsError) as error:
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_PARSE_FAILED,
                               value=(assertion_title, index, value_preview(i.get('expect')), error.msg)) from error
        if assertion_type == 'cache':
            expression = str(raw_expression).strip()
        else:
            try:
                expression = self.test_setup.test_data.replace(raw_expression)
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_EXPRESSION_PARSE_FAILED,
                                   value=(assertion_title, index, value_preview(raw_expression), error.msg)) from error
        log.api.debug(f'开始响应提取断言，类型：{assertion_type}，表达式：{expression}，预期：{expect}')
        if not expression:
            expression_names = {'jsonpath': 'JSONPath', 'regex': '正则表达式', 'cache': '缓存表达式'}
            expression_name = expression_names.get(assertion_type, '提取表达式')
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CONFIG_REQUIRED,
                               value=(assertion_title, index, expression_name))
        if assertion_type == 'regex':
            extracted_value, extraction_message = self.__extract_regex_assertion_value(
                response.text,
                expression,
                index,
            )
        elif assertion_type == 'jsonpath':
            try:
                ensure_jsonpath_source(response.json)
            except AutoApiError as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_JSONPATH_JSON_FAILED,
                                   value=(assertion_title, index, expression, error.msg)) from error
            extracted_value = extract_jsonpath_value(
                response.json,
                expression,
                operation=f'{assertion_title}取值（第{index}项）',
            )
            extraction_message = '已通过JSONPath提取响应JSON字段'
        else:
            cache_key = expression[3:-2].strip()
            try:
                extracted_value = self.test_setup.test_data.get_cache(cache_key)
            except (MangoServerError, MangoToolsError) as error:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_FAILED,
                                   value=(index, expression, cache_key, error.msg)) from error
            if extracted_value is None:
                raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_CACHE_ASSERTION_EXPRESSION_NOT_FOUND,
                                   value=(index, expression, cache_key))
            extraction_message = f'已从当前用例运行缓存读取Key【{cache_key}】'
        resolved_config = dict(i)
        resolved_config['assertion_type'] = assertion_type
        resolved_config['actual'] = expression
        return {
            'expect': expect,
            'actual': extracted_value,
            'method': i.get('method'),
            '_assertion_source': {
                'index': index,
                'source_type': assertion_type,
                'actual_source': (raw_i or i).get('actual'),
                'expect_source': (raw_i or i).get('expect'),
                'raw_config': raw_i or i,
                'resolved_config': resolved_config,
                'extraction_message': extraction_message,
            }
        }

    def __ass_general(
            self,
            general: list[dict],
            raw_general: list[dict] | None = None,
            continue_on_failure: bool = False,
    ):
        self.__run_group_assertions(
            general,
            self.__build_general_ass_dict,
            raw_general,
            default_source_type='general',
            continue_on_failure=continue_on_failure,
        )

    def __build_general_ass_dict(self, i: dict, raw_i: dict | None = None, index: int = 1):
        try:
            value = self.test_setup.test_data.replace(i.get('value') or {})
        except (MangoServerError, MangoToolsError) as error:
            raise AutoApiError(
                AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_PARSE_FAILED_CODE_ASSERTION_CONFIG_PARSE_FAILED,
                value=(index, error.msg)) from error
        raw_value = (raw_i or i).get('value') or {}
        ass_dict = {
            'method': value.get('value'),
            'actual': '',
            'expect': ''
        }
        parameters = value.get('parameter', [])
        for p in parameters:
            ass_dict[p.get('f')] = p.get('v')
        if not ass_dict.get('method'):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_REQUIRED_CODE_ASSERTION_CONFIG_REQUIRED,
                               value=(index,))
        if not any(p.get('f') == 'actual' for p in parameters):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_INVALID, value=(index,))
        raw_parameter_map = {
            p.get('f'): p.get('v')
            for p in raw_value.get('parameter', [])
            if isinstance(p, dict)
        }
        resolved_config = dict(i)
        resolved_config['value'] = value
        ass_dict['_assertion_source'] = {
            'index': index,
            'source_type': 'general',
            'actual_source': raw_parameter_map.get('actual', ass_dict.get('actual')),
            'expect_source': raw_parameter_map.get('expect', ass_dict.get('expect')),
            'raw_config': raw_i or i,
            'resolved_config': resolved_config,
        }
        return ass_dict

    def __run_group_assertions(
            self,
            assertions: list[dict],
            build_ass_dict,
            raw_assertions: list[dict] | None = None,
            default_source_type: str = 'general',
            continue_on_failure: bool = False,
    ):
        normal_assertions = []
        grouped_assertions = {}
        for index, i in enumerate(assertions, start=1):
            raw_index = index - 1
            raw_i = raw_assertions[raw_index] if isinstance(raw_assertions, list) and raw_index < len(
                raw_assertions) else i
            group_name = (i.get('group_name') or '').strip()
            if not group_name:
                normal_assertions.append((index, i, raw_i))
                continue
            grouped_assertions.setdefault(group_name, []).append((index, i, raw_i))

        mango_assertion = ObtainAssertion(mysql_conn=None, test_data=self.test_data)
        failure_messages = []
        if default_source_type == 'jsonpath' and normal_assertions \
                and (normal_assertions[0][1].get('group_logic') or 'AND').upper() == 'OR':
            try:
                self.__ass_group(
                    mango_assertion,
                    '未分组',
                    normal_assertions,
                    build_ass_dict,
                    default_source_type=default_source_type,
                    continue_on_failure=continue_on_failure,
                )
            except AutoApiError as error:
                if not continue_on_failure:
                    raise
                failure_messages.append(error.msg)
            normal_assertions = []
        for index, i, raw_i in normal_assertions:
            result_count = len(self.ass_result)
            try:
                self.__ass_(mango_assertion, build_ass_dict(i, raw_i, index), API_ASSERTION_FAILED)
            except AutoApiError as error:
                if not continue_on_failure:
                    raise
                failure_messages.append(error.msg)
                if len(self.ass_result) == result_count:
                    source_type = str(i.get('assertion_type') or default_source_type).lower()
                    title = '响应字段断言' if source_type != 'general' else '通用断言'
                    self.__append_assertion_error(
                        title, source_type, error.msg, raw_config=raw_i, assertion_index=index,
                    )
        for group_name, group_items in grouped_assertions.items():
            try:
                self.__ass_group(
                    mango_assertion,
                    group_name,
                    group_items,
                    build_ass_dict,
                    default_source_type=default_source_type,
                    continue_on_failure=continue_on_failure,
                )
            except AutoApiError as error:
                if not continue_on_failure:
                    raise
                failure_messages.append(error.msg)
        if failure_messages:
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=('；'.join(failure_messages),))

    def __ass_group(
            self,
            mango_assertion,
            group_name: str,
            group_items: list[tuple[int, dict, dict]],
            build_ass_dict,
            default_source_type: str = 'general',
            continue_on_failure: bool = False,
    ):
        group_logic = (group_items[0][1].get('group_logic') or 'AND').upper()
        if group_logic not in {'AND', 'OR'}:
            group_logic = 'AND'
        passed_count = 0
        first_error = None
        start_index = len(self.ass_result)
        for index, i, raw_i in group_items:
            result_count = len(self.ass_result)
            try:
                self.__ass_(
                    mango_assertion,
                    build_ass_dict(i, raw_i, index),
                    API_ASSERTION_FAILED,
                    group_name=group_name,
                    group_logic=group_logic,
                )
                passed_count += 1
            except AutoApiError as error:
                if continue_on_failure and len(self.ass_result) == result_count:
                    source_type = str(i.get('assertion_type') or default_source_type).lower()
                    title = '响应字段断言' if source_type != 'general' else '通用断言'
                    self.__append_assertion_error(
                        title,
                        source_type,
                        error.msg,
                        raw_config=raw_i,
                        group_name=group_name,
                        group_logic=group_logic,
                        assertion_index=index,
                    )
                if first_error is None:
                    first_error = error

        group_passed = passed_count == len(group_items) if group_logic == 'AND' else passed_count > 0
        for ass_result in self.ass_result[start_index:]:
            ass_result.group_result = group_passed
        summary = ApiAssertionResult(
            method=f'{group_logic}断言组',
            actual=f'通过 {passed_count} 条 / 共 {len(group_items)} 条',
            expect=group_name,
            ass_msg=f'{group_logic}组【{group_name}】{"通过" if group_passed else "失败"}：'
                    f'共{len(group_items)}条，{passed_count}条通过，{len(group_items) - passed_count}条失败',
            status=StatusEnum.SUCCESS.value if group_passed else StatusEnum.FAIL.value,
            group_name=group_name,
            group_logic=group_logic,
            group_result=group_passed,
            source_type='assertion_group',
            group_source_type=default_source_type,
            raw_config=[raw_i for _, _, raw_i in group_items],
            resolved_config=[i for _, i, _ in group_items],
        )
        self.ass_result.append(summary)
        if not group_passed and first_error:
            group_title = '且' if group_logic == 'AND' else '或'
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_RESULT_FAILED,
                               value=(group_title, group_name, len(group_items), passed_count,
                                      len(group_items) - passed_count))

    def __ass_sql(self, sql_list: list[dict], continue_on_failure: bool = False):
        from src.apps.auto_api.services.base.data_source_operation import (
            DataSourceAssertionConnection,
            execute_data_source_assertion,
        )

        failure_messages = []
        for index, sql in enumerate(sql_list, start=1):
            result_count = len(self.ass_result)
            try:
                if not isinstance(sql, dict):
                    raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_SQL_ASSERTION_CONFIG_INVALID, value=(index,))
                if not should_execute_sql(sql, self.test_env):
                    log.api.info(
                        f'用例场景SQL断言跳过执行，当前环境：{self.test_env}，配置环境：{sql.get("test_envs")}'
                    )
                    continue
                raw_config = dict(sql)
                ass_dict = {
                    'expect': self.test_setup.test_data.replace(sql.get('expect')),
                    'actual': self.test_setup.test_data.replace(sql.get('actual')),
                    'method': sql.get('method'),
                }
                ass_dict['_assertion_source'] = {
                    'index': index,
                    'source_type': 'sql',
                    'actual_source': sql.get('actual'),
                    'expect_source': sql.get('expect'),
                    'raw_config': raw_config,
                    'resolved_config': {
                        **raw_config,
                        'actual': ass_dict['actual'],
                        'expect': ass_dict['expect'],
                    },
                }
                execution_result = execute_data_source_assertion(
                    self.test_setup,
                    self.test_env,
                    {
                        'datasource_alias': sql.get('datasource_alias'),
                        'value': ass_dict['actual'],
                    },
                    source_context=self.__sql_source_context('sql_assertion', index),
                )
                mango_assertion = ObtainAssertion(
                    mysql_conn=DataSourceAssertionConnection(execution_result),
                    test_data=self.test_data,
                )
                self.__ass_(mango_assertion, ass_dict, API_ASSERTION_FAILED)
            except (AutoApiError, AutoApiError, MangoToolsError) as error:
                if not continue_on_failure:
                    raise
                failure_messages.append(error.msg)
                if len(self.ass_result) == result_count:
                    self.__append_assertion_error(
                        'SQL断言',
                        'sql',
                        error.msg,
                        raw_config=sql if isinstance(sql, dict) else None,
                    )
            except Exception as error:
                if not continue_on_failure:
                    raise
                error_message = f'SQL断言发生未知错误（第{index}项）：{error}'
                failure_messages.append(error_message)
                if len(self.ass_result) == result_count:
                    self.__append_assertion_error(
                        'SQL断言',
                        'sql',
                        error_message,
                        raw_config=sql if isinstance(sql, dict) else None,
                    )
        if failure_messages:
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=('；'.join(failure_messages),))

    @staticmethod
    def __assertion_summary_value(value) -> str:
        return value_preview(value, max_length=80).replace('\r', '\\r').replace('\n', '\\n')

    @classmethod
    def __assertion_failure_summary(
            cls,
            title: str,
            actual,
            expect,
            assertion_index: int | None = None,
    ) -> str:
        index_context = f'（第{assertion_index}项）' if assertion_index is not None else ''
        return (
            f'{title}{index_context}：实际={cls.__assertion_summary_value(actual)}，'
            f'预期={cls.__assertion_summary_value(expect)}；详情见断言结果'
        )

    def __ass_json_all(self, actual: dict, expect: dict):
        log.api.debug(f'用例详情断言-3->实际：{actual}，预期：{expect}')
        ass_result = ApiAssertionResult(
            method='JSON一致性断言',
            expect=json.dumps(expect, ensure_ascii=False),
            source_type='json_all',
            expect_source=getattr(self.parameter, 'ass_json_all', None),
            raw_config=getattr(self.parameter, 'ass_json_all', None),
            resolved_config=expect,
        )
        ass_result.actual = json.dumps(actual, ensure_ascii=False)
        if not is_jsonpath_source(actual):
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = (
                f'JSON一致断言失败：响应JSON类型为【{json_value_type(actual)}】，只支持对象或数组'
            )
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('JSON一致断言失败', actual, expect),))
        if not is_jsonpath_source(expect):
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = (
                f'JSON一致断言配置错误：预期JSON类型为【{json_value_type(expect)}】，只支持对象或数组'
            )
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('JSON一致断言配置错误', actual, expect),))
        difference = describe_json_consistency(actual, expect)
        if difference:
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = f'JSON一致断言失败：{difference}'
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('JSON一致断言失败', actual, expect),))
        ass_result.ass_msg = 'JSON一致断言通过：响应JSON包含全部预期内容'
        self.ass_result.append(ass_result)

    def __ass_test_all(self, actual: str, expect: str):
        log.api.debug(f'用例详情断言-4->实际：{actual}，预期：{expect}')
        ass_result = ApiAssertionResult(
            method='文本一致性断言',
            actual=actual,
            expect=expect,
            ass_msg=f'实际={actual}, 预期={expect}',
            source_type='text_all',
            actual_source='response.text',
            expect_source=getattr(self.parameter, 'ass_text_all', None),
            raw_config=getattr(self.parameter, 'ass_text_all', None),
            resolved_config=expect,
        )
        if actual is None:
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = '文本一致断言失败：当前响应没有文本内容，无法执行文本比较'
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('文本一致断言失败', actual, expect),))
        if not isinstance(actual, str) or not isinstance(expect, str):
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = (
                f'文本一致断言配置错误：实际值类型为【{type(actual).__name__}】，'
                f'预期值类型为【{type(expect).__name__}】，两者都必须是字符串'
            )
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('文本一致断言配置错误', actual, expect),))
        normalized_actual = actual.strip()
        normalized_expect = expect.strip()
        if normalized_actual != normalized_expect:
            difference_index = first_text_difference(normalized_actual, normalized_expect)
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = (
                f'文本一致断言失败：去除首尾空白后内容不一致，首次差异位于第'
                f'【{difference_index}】个字符；实际长度【{len(normalized_actual)}】，'
                f'预期长度【{len(normalized_expect)}】；实际摘要：【{value_preview(normalized_actual)}】，'
                f'预期摘要：【{value_preview(normalized_expect)}】'
            )
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=(
                self.__assertion_failure_summary('文本一致断言失败', normalized_actual, normalized_expect),))
        ass_result.ass_msg = '文本一致断言通过：去除首尾空白后内容一致'
        self.ass_result.append(ass_result)

    def __ass_schema(self, response):
        actual = response.json
        expect = None
        if self.parameter.ass_schema:
            expect = self.parameter.ass_schema
        if expect is None:
            return
        log.api.debug(f'用例详情断言-5->实际：{actual}，预期：{expect}')
        ass_result = ApiAssertionResult(
            method='结构断言',
            actual=actual,
            expect=expect,
            ass_msg=f'实际={actual}, 预期={expect}',
            source_type='schema',
            actual_source='response.json',
            expect_source=getattr(self.parameter, 'ass_schema', None),
            raw_config=getattr(self.parameter, 'ass_schema', None),
            resolved_config=expect,
        )
        try:
            validate(instance=actual, schema=expect)
            ass_result.ass_msg = '结构化断言通过：响应JSON符合Schema配置'
            self.ass_result.append(ass_result)
        except jsonschema.exceptions.ValidationError as error:
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = f'结构化断言失败：{describe_schema_validation(error)}'
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR,
                               value=(self.__assertion_failure_summary('结构化断言失败', actual, expect),)) from error
        except jsonschema.exceptions.SchemaError as error:
            ass_result.status = StatusEnum.FAIL.value
            ass_result.ass_msg = f'结构化断言配置错误：{describe_schema_config(error)}'
            self.ass_result.append(ass_result)
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=(
                self.__assertion_failure_summary('结构化断言配置错误', actual, expect),)) from error

    def __ass_(
            self,
            mango_assertion,
            ass_dict: dict,
            _error_msg: ErrorDefinition,
            group_name: str | None = None,
            group_logic: str | None = None
    ):
        assertion_source = ass_dict.get('_assertion_source') or {}
        execute_ass_dict = {key: value for key, value in ass_dict.items() if key != '_assertion_source'}
        assertion_index = assertion_source.get('index', 1)
        source_type = assertion_source.get('source_type')
        assertion_titles = {
            'jsonpath': 'JSONPath提取断言',
            'regex': '正则提取断言',
            'cache': '缓存值断言',
            'general': '通用断言',
            'sql': 'SQL断言',
        }
        assertion_title = assertion_titles.get(source_type, '通用断言')
        extraction_type_titles = {
            'jsonpath': 'JSONPath',
            'regex': '正则表达式',
            'cache': '缓存值',
        }
        method = execute_ass_dict.get('method')
        method_func = getattr(mango_assertion, method, None) if method else None
        if not callable(method_func):
            raise AutoApiError(AUTO_API_BASE_CASE_PARAMETER_ASSERTION_CONFIG_NOT_FOUND,
                               value=(assertion_title, assertion_index, method or '未设置'))
        method_title = (method_func.__doc__ or method).replace('expect', '预期值')
        ass_result = ApiAssertionResult(
            method=method_title,
            actual=execute_ass_dict['actual'],
            expect=execute_ass_dict['expect'],
            group_name=group_name,
            group_logic=group_logic,
            source_type=assertion_source.get('source_type'),
            assertion_index=assertion_index,
            actual_source=assertion_source.get('actual_source'),
            expect_source=assertion_source.get('expect_source'),
            raw_config=assertion_source.get('raw_config'),
            resolved_config=assertion_source.get('resolved_config'),
        )
        log.api.debug(f'用例详情断言-1->{execute_ass_dict}')
        group_context = ''
        if group_name:
            relation_title = '且' if group_logic == 'AND' else '或'
            group_context = f'，关系：【{relation_title}】，断言组：【{group_name}】'
        source_context = ''
        if assertion_source.get('actual_source') not in [None, '']:
            source_names = {
                'regex': '正则表达式',
                'cache': '缓存表达式',
            }
            source_name = source_names.get(source_type, '提取表达式' if source_type == 'jsonpath' else '实际值来源')
            source_context = f'，{source_name}：【{value_preview(assertion_source.get("actual_source"))}】'
        extraction_message = assertion_source.get('extraction_message')
        if extraction_message:
            source_context += f'，提取说明：【{extraction_message}】'
        try:
            assertion_message = mango_assertion.ass(**execute_ass_dict)
            if extraction_message:
                ass_result.ass_msg = f'{assertion_title}通过：{extraction_message}；{assertion_message}'
            else:
                ass_result.ass_msg = assertion_message
            self.ass_result.append(ass_result)
        except AssertionError as error:
            reason = str(error.args[0]) if error.args else '断言条件不成立'
            expect_context = ''
            if execute_ass_dict.get('expect') is not None:
                expect_context = f'，预期值：【{typed_value(execute_ass_dict.get("expect"))}】'
            if source_type in extraction_type_titles:
                ass_result.ass_msg = reason
            else:
                ass_result.ass_msg = (
                    f'{assertion_title}失败（第{assertion_index}项，方法：【{method_title}】{group_context}）'
                    f'{source_context}，实际值：【{typed_value(execute_ass_dict.get("actual"))}】'
                    f'{expect_context}；原因：{reason}'
                )
            ass_result.status = StatusEnum.FAIL.value
            self.ass_result.append(ass_result)
            summary_title = '响应提取断言失败' if source_type in extraction_type_titles else f'{assertion_title}失败'
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=(
                self.__assertion_failure_summary(summary_title, execute_ass_dict.get('actual'),
                                                 execute_ass_dict.get('expect'), assertion_index),))
        except (TypeError, ValueError, re.error, MangoToolsError) as error:
            log.api.error(f'用例详情断言-2：{error}')
            reason = error.msg if isinstance(error, MangoToolsError) else str(error)
            ass_result.status = StatusEnum.FAIL.value
            if source_type in extraction_type_titles:
                ass_result.ass_msg = f'执行异常：{reason}'
            else:
                ass_result.ass_msg = (
                    f'{assertion_title}执行失败（第{assertion_index}项，方法：【{method_title}】{group_context}）'
                    f'{source_context}，实际值：【{typed_value(execute_ass_dict.get("actual"))}】，'
                    f'预期值：【{typed_value(execute_ass_dict.get("expect"))}】；错误：{reason}'
                )
            self.ass_result.append(ass_result)
            summary_title = '响应提取断言执行失败' \
                if source_type in extraction_type_titles else f'{assertion_title}执行失败'
            raise AutoApiError(AUTO_API_DYNAMIC_ERROR, value=(
                self.__assertion_failure_summary(summary_title, execute_ass_dict.get('actual'),
                                                 execute_ass_dict.get('expect'), assertion_index),)) from error

    def __front_sql(self, front_sql):
        for index, i in enumerate(front_sql or [], start=1):
            if not should_execute_sql(i, self.test_env):
                log.api.info(
                    f'用例场景前置SQL跳过执行，当前环境：{self.test_env}，配置环境：{i.get("test_envs")}'
                )
                continue
            key = self.test_setup.test_data.replace(i.get('key'))
            value = self.test_setup.test_data.replace(i.get('value'))
            log.api.debug(f'用例场景前置sql-1->key:{key}，value:{value}')
            if not value:
                raise AutoApiError(API_CASE_PRE_SQL_EMPTY)
            result = execute_data_source_operation(
                self.test_setup,
                self.test_env,
                i,
                source_context=self.__sql_source_context('parameter_front', index),
            )
            log.api.debug(f'用例场景前置数据库操作->key:{key}，result:{result}')
            if key:
                cache_data_source_result(self.test_setup, key, result)

    def __sql_source_context(self, source_stage: str, operation_index: int) -> dict:
        case_id = getattr(getattr(self.parameter, 'case_detailed', None), 'case_id', None)
        return {
            'source_type': 'api_case_parameter',
            'source_stage': source_stage,
            'source_id': self.parameter.id,
            'case_id': case_id,
            'parameter_id': self.parameter.id,
            'api_info_id': getattr(self.api_info, 'id', None),
            'operation_index': operation_index,
        }

    def __front_func(self, front_func: str, request: ApiExecutionRequest) -> ApiExecutionRequest:
        log.api.debug(f'用例详情前置-2->{front_func}')
        return self.test_setup.execute_analytic_func(
            front_func,
            self,
            request,
            error_msg=API_CASE_PRE_FUNCTION_FAILED,
        )
