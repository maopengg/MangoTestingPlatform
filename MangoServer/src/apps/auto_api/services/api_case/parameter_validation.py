import inspect
import re

from mangotools.data_processor import JsonTool, RegexTool
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.exceptions import (
    API_EXTRACTION_CONFIG_INVALID,
    API_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_CONFIG_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_RESPONSE_ASSERTION_EXPRESSION_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_REGEX_RESPONSE_ASSERTION_EXPRESSION_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED_CODE_RESPONSE_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_TYPE_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED_CODE_SQL_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_OUT_OF_RANGE,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import (
    ApiGeneralAssertionItem,
    ApiJsonPathAssertionItem,
    ApiKeyValueItem,
    ApiSqlAssertionItem,
    normalize_body_config_by_type,
    validate_body_config,
    validate_data_source_operation_list,
    validate_int_list,
    validate_json_object,
    validate_model_list,
)
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.common.testing import ObtainAssertion


class ApiCaseParameterValidationService:
    @staticmethod
    def project_product_id(payload: dict, instance: ApiCaseDetailedParameter | None) -> int | None:
        detailed_id = payload.get("case_detailed") or getattr(instance, "case_detailed_id", None)
        return ApiCaseDetailed.objects.filter(id=detailed_id).values_list(
            "case__project_product_id", flat=True,
        ).first()

    @classmethod
    def validate(cls, payload: dict, instance: ApiCaseDetailedParameter | None = None) -> dict:
        attrs = dict(payload)
        project_product_id = cls.project_product_id(attrs, instance)
        detailed_id = attrs.get("case_detailed") or getattr(instance, "case_detailed_id", None)
        detailed = ApiCaseDetailed.objects.select_related("api_info").filter(id=detailed_id).first()
        body_type = None
        if detailed and detailed.api_info:
            body_type = ApiCaseStepService.resolve_step_api_runtime(detailed, allow_draft=True).body_type
        if "body_config" in attrs:
            attrs["body_config"] = normalize_body_config_by_type(
                body_type,
                validate_body_config(attrs.get("body_config"), "请求体配置"),
            )
        if "sse_config" in attrs:
            attrs["sse_config"] = validate_body_config(attrs["sse_config"], "SSE配置")
        if "headers" in attrs:
            attrs["headers"] = validate_int_list(attrs["headers"], "请求头")
        for field, label in (("front_sql", "前置数据库操作"), ("posterior_sql", "后置数据库操作")):
            if field in attrs:
                attrs[field] = validate_data_source_operation_list(attrs[field], label, project_product_id)
        if "ass_general" in attrs:
            attrs["ass_general"] = cls.validate_general(attrs["ass_general"])
        if "ass_sql" in attrs:
            attrs["ass_sql"] = cls.validate_sql(attrs["ass_sql"], project_product_id)
        if "ass_json_all" in attrs:
            attrs["ass_json_all"] = validate_json_object(attrs["ass_json_all"], "响应JSON全匹配断言", allow_list=True)
        if "ass_jsonpath" in attrs:
            attrs["ass_jsonpath"] = cls.validate_jsonpath(attrs["ass_jsonpath"])
        if "ass_schema" in attrs:
            attrs["ass_schema"] = validate_json_object(attrs["ass_schema"], "schema配置")
        for field, label in (("posterior_response", "响应JSON提取"), ("posterior_response_text", "响应文本提取")):
            if field in attrs:
                attrs[field] = cls.validate_extract(attrs[field], label)
        if "posterior_sleep" in attrs:
            value = attrs["posterior_sleep"]
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_INVALID, value=(value,))
            if value is not None and not 0 <= value <= 32767:
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_OUT_OF_RANGE, value=(value,))
        if "posterior_file" in attrs:
            attrs["posterior_file"] = validate_model_list(
                attrs["posterior_file"], ApiKeyValueItem, "文件下载",
                allow_none=True, allow_empty_dict=True,
            )
        return attrs

    @staticmethod
    def validate_general(value):
        items = validate_model_list(value, ApiGeneralAssertionItem, "通用断言")
        assertion = ObtainAssertion(mysql_conn=None, test_data=None)
        for index, item in enumerate(items, start=1):
            method = (item.get("value") or {}).get("value")
            if not method:
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_REQUIRED, value=(index,))
            if not callable(getattr(assertion, method, None)):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_NOT_FOUND, value=(index, method))
            if not any(
                    parameter.get("f") == "actual" for parameter in (item.get("value") or {}).get("parameter") or []):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_CONFIG_INVALID, value=(index,))
        return items

    @staticmethod
    def validate_sql(value, project_product_id):
        items = validate_model_list(value, ApiSqlAssertionItem, "SQL断言")
        assertion = ObtainAssertion(mysql_conn=None, test_data=None)
        for index, item in enumerate(items, start=1):
            method = item.get("method")
            method_func = getattr(assertion, method, None) if method else None
            if not callable(method_func) or not str(method).startswith("assert_sql_"):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_NOT_FOUND,
                                   value=(index, method or "未设置"))
            if item.get("actual") in (None, ""):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED, value=(index,))
            expect = inspect.signature(method_func).parameters.get("expect")
            if expect is not None and expect.default is inspect.Parameter.empty and item.get("expect") in (None, ""):
                raise AutoApiError(
                    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED_CODE_SQL_ASSERTION_REQUIRED,
                    value=(index,))
            if item.get("datasource_alias") in (None, ""):
                raise AutoApiError(API_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED)
        operations = validate_data_source_operation_list([
            {
                "value": item.get("actual"),
                "datasource_alias": item.get("datasource_alias"),
                "test_envs": item.get("test_envs") or [],
            }
            for item in items
        ], "SQL断言", project_product_id)
        for item, operation in zip(items, operations):
            item["datasource_alias"] = operation["datasource_alias"]
            item["test_envs"] = operation["test_envs"]
        return items

    @staticmethod
    def validate_jsonpath(value):
        items = validate_model_list(value, ApiJsonPathAssertionItem, "响应jsonpath断言")
        assertion = ObtainAssertion(mysql_conn=None, test_data=None)
        for index, item in enumerate(items, start=1):
            assertion_type = str(item.get("assertion_type") or "jsonpath").lower()
            item["assertion_type"] = assertion_type
            if assertion_type not in {"jsonpath", "regex", "cache"}:
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_TYPE_NOT_FOUND,
                                   value=(index, assertion_type))
            if not item.get("actual"):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED, value=(index, {
                    "jsonpath": "JSONPath", "regex": "正则表达式", "cache": "缓存表达式"}[assertion_type]))
            if assertion_type == "regex":
                try:
                    if '${{' not in item['actual']:
                        RegexTool.compile(item["actual"])
                except MangoToolsError as error:
                    raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_REGEX_RESPONSE_ASSERTION_EXPRESSION_INVALID,
                                       value=(index, error.msg)) from error
            if assertion_type == 'jsonpath' and '${{' not in item['actual']:
                try:
                    JsonTool.validate_json_path_expression(item['actual'])
                except MangoToolsError as error:
                    raise AutoApiError(API_EXTRACTION_CONFIG_INVALID,
                                       value=('响应JSONPath断言', index, error.msg)) from error
            if assertion_type == "cache" and not re.fullmatch(r"\$\{\{[^{}]+\}\}", str(item["actual"]).strip()):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_RESPONSE_ASSERTION_EXPRESSION_INVALID,
                                   value=(index,))
            method = item.get("method")
            if not method:
                raise AutoApiError(
                    AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_REQUIRED_CODE_RESPONSE_ASSERTION_REQUIRED,
                    value=(index,))
            if not callable(getattr(assertion, method, None)):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_RESPONSE_ASSERTION_NOT_FOUND,
                                   value=(index, method))
        return items

    @staticmethod
    def validate_extract(value, field_name):
        items = validate_model_list(value, ApiKeyValueItem, field_name)
        for index, item in enumerate(items, start=1):
            if not item.get("key"):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_CACHE_REQUIRED, value=(field_name, index))
            if not item.get("value"):
                label = "JSONPath" if field_name == "响应JSON提取" else "正则表达式"
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_REQUIRED, value=(field_name, index, label))
            if '${{' not in item['value']:
                try:
                    if field_name == '响应JSON提取':
                        JsonTool.validate_json_path_expression(item['value'])
                    else:
                        RegexTool.compile(item['value'])
                except MangoToolsError as error:
                    raise AutoApiError(API_EXTRACTION_CONFIG_INVALID,
                                       value=(field_name, index, error.msg)) from error
        return items
