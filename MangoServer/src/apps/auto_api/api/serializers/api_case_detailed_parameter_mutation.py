import inspect

from rest_framework import serializers

from src.apps.auto_api.exceptions import (
    API_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_OUT_OF_RANGE,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_CONFIG_INVALID,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_NOT_FOUND,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED_CODE_SQL_ASSERTION_REQUIRED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import (
    ApiGeneralAssertionItem,
    ApiKeyValueItem,
    ApiSqlAssertionItem,
    normalize_body_config_by_type,
    merge_scenario_protocol_config,
    validate_body_config,
    validate_int_list,
    validate_json_object,
    validate_model_list,
    validate_data_source_operation_list,
)
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
from src.common.testing import ObtainAssertion


class ApiCaseDetailedParameterSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseDetailedParameter
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset

    def validate_headers(self, value):
        return validate_int_list(value, '请求头')

    def validate_body_config(self, value):
        return validate_body_config(value, '请求体配置')

    def validate_sse_config(self, value):
        return validate_body_config(value, 'SSE配置')

    def validate(self, attrs):
        mcp_config = attrs.pop('mcp_config', None)
        grpc_config = attrs.pop('grpc_config', None)
        protocol_expectation = attrs.pop('protocol_expectation', None)
        if (
                'body_config' in attrs
                or mcp_config not in (None, '')
                or grpc_config not in (None, '')
                or protocol_expectation not in (None, '')
        ):
            attrs['body_config'] = merge_scenario_protocol_config(
                attrs.get('body_config', getattr(self.instance, 'body_config', None)),
                mcp_config,
                grpc_config,
                protocol_expectation,
            )
        for legacy_field in ('data', 'json', 'file', 'protocol_type', 'body_type', 'result_data'):
            attrs.pop(legacy_field, None)
        case_detailed = attrs.get('case_detailed') or getattr(self.instance, 'case_detailed', None)
        body_type = None
        if case_detailed and case_detailed.api_info:
            body_type = ApiCaseStepService.resolve_step_api_runtime(case_detailed, allow_draft=True).body_type
        if 'body_config' in attrs:
            attrs['body_config'] = normalize_body_config_by_type(body_type, attrs.get('body_config'))
        return attrs

    def validate_front_sql(self, value):
        return validate_data_source_operation_list(value, '前置数据库操作', self._project_product_id())

    def validate_ass_general(self, value):
        items = validate_model_list(value, ApiGeneralAssertionItem, '通用断言')
        assertion = ObtainAssertion(mysql_conn=None, test_data=None)
        for index, item in enumerate(items, start=1):
            method = (item.get('value') or {}).get('value')
            if not method:
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_REQUIRED, value=(index,))
            if not callable(getattr(assertion, method, None)):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_NOT_FOUND, value=(index, method))
            parameters = (item.get('value') or {}).get('parameter') or []
            if not any(parameter.get('f') == 'actual' for parameter in parameters):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_ASSERTION_CONFIG_INVALID, value=(index,))
        return items

    def validate_ass_sql(self, value):
        items = validate_model_list(value, ApiSqlAssertionItem, 'SQL断言')
        assertion = ObtainAssertion(mysql_conn=None, test_data=None)
        for index, item in enumerate(items, start=1):
            method = item.get('method')
            method_func = getattr(assertion, method, None) if method else None
            if not callable(method_func) or not str(method).startswith('assert_sql_'):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_NOT_FOUND,
                                   value=(index, method or '未设置'))
            if item.get('actual') in (None, ''):
                raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED, value=(index,))
            method_parameters = inspect.signature(method_func).parameters
            expect_parameter = method_parameters.get('expect')
            if (
                    expect_parameter is not None
                    and expect_parameter.default is inspect.Parameter.empty
                    and item.get('expect') in (None, '')
            ):
                raise AutoApiError(
                    AUTO_API_API_CASE_DETAILED_PARAMETER_SQL_ASSERTION_REQUIRED_CODE_SQL_ASSERTION_REQUIRED,
                    value=(index,))
            if item.get('datasource_alias') in (None, ''):
                raise AutoApiError(API_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED)
        validated_operations = validate_data_source_operation_list(
            [
                {
                    'value': item.get('actual'),
                    'datasource_alias': item.get('datasource_alias'),
                    'test_envs': item.get('test_envs') or [],
                }
                for item in items
            ],
            'SQL断言',
            self._project_product_id(),
        )
        for item, operation in zip(items, validated_operations):
            item['datasource_alias'] = operation['datasource_alias']
            item['test_envs'] = operation['test_envs']
        return items

    def validate_ass_json_all(self, value):
        return validate_json_object(value, '响应JSON全匹配断言', allow_list=True)

    def validate_ass_jsonpath(self, value):
        return ApiCaseParameterValidationService.validate_jsonpath(value)

    def validate_ass_schema(self, value):
        return validate_json_object(value, 'schema配置')

    def validate_posterior_sql(self, value):
        return validate_data_source_operation_list(value, '后置数据库操作', self._project_product_id())

    def _project_product_id(self):
        case_detailed = self.initial_data.get('case_detailed')
        if isinstance(case_detailed, dict):
            case_detailed = case_detailed.get('id')
        if case_detailed in [None, ''] and self.instance:
            case_detailed = self.instance.case_detailed_id
        return ApiCaseDetailed.objects.filter(id=case_detailed).values_list(
            'case__project_product_id',
            flat=True,
        ).first()

    def validate_posterior_response(self, value):
        return self._validate_posterior_extract(value, '响应JSON提取')

    def validate_posterior_response_text(self, value):
        return self._validate_posterior_extract(value, '响应文本提取')

    @staticmethod
    def _validate_posterior_extract(value, field_name):
        return ApiCaseParameterValidationService.validate_extract(value, field_name)

    def validate_posterior_sleep(self, value):
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, int):
            raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_INVALID, value=(value,))
        if value < 0 or value > 32767:
            raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_TIME_OUT_OF_RANGE, value=(value,))
        return value

    def validate_posterior_file(self, value):
        return validate_model_list(value, ApiKeyValueItem, '文件下载', allow_none=True, allow_empty_dict=True)
