# -*- coding: utf-8 -*-
import copy

from mangotools.enums import StatusEnum
from pydantic import ValidationError

from src.apps.auto_api.exceptions import (
    AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_PARAMETER_NOT_FOUND,
    AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_RESULT_EXECUTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_RESULT_EXECUTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_CONFIG_REQUIRED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED_CODE_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED_CODE_JSON_ASSERTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED_CODE_ASSERTION_FAILED,
    AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_EXECUTION_FAILED,
    AUTO_API_ASSERTION_VALUE_ARRAY_REQUIRED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.apps.test_center.services.execution_result import ExecutionResultService


class ApiAssertionVerificationService:
    ASSERTION_FIELDS = (
        'ass_json_all',
        'ass_text_all',
        'ass_jsonpath',
        'ass_sql',
        'ass_schema',
        'ass_general',
    )

    @classmethod
    def verify(cls, parameter_id: int, assertions: dict, test_env: int = 0) -> dict:
        parameter = (
            ApiCaseDetailedParameter.objects
            .select_related('case_detailed__api_info')
            .filter(id=parameter_id)
            .first()
        )
        if not parameter:
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_PARAMETER_NOT_FOUND,
                               value=(parameter_id,))
        if not isinstance(assertions, dict):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED)

        cls._validate_assertion_payload(assertions)
        result_data = ExecutionResultService.latest_api_case_parameter_result(
            case_id=parameter.case_detailed.case_id,
            parameter_id=parameter.id,
            test_env=test_env,
        )
        if not isinstance(result_data, dict):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_RESULT_EXECUTION_FAILED)
        response_data = result_data.get('response')
        if not isinstance(response_data, dict):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_RESULT_EXECUTION_FAILED)
        try:
            response = ApiExecutionResponse.model_validate(response_data)
        except ValidationError as error:
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_RESPONSE_ASSERTION_EXECUTION_FAILED,
                               value=(error,)) from error

        verify_parameter = copy.copy(parameter)
        for field in cls.ASSERTION_FIELDS:
            if field in assertions:
                setattr(verify_parameter, field, assertions.get(field))

        api_info = parameter.case_detailed.api_info
        if not cls._has_assertion(verify_parameter, api_info):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_SCENARIO_ASSERTION_CONFIG_REQUIRED)

        test_setup = APIBaseTestSetup()
        if getattr(verify_parameter, 'ass_sql', None):
            test_setup.init_test_object(api_info.project_product_id, test_env)
        cache_data = result_data.get('cache_data') or result_data.get('cache_all') or {}
        if not isinstance(cache_data, dict):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED)
        for key, value in cache_data.items():
            test_setup.test_data.set_cache(key, value)
        data_factory_cache = result_data.get('data_factory_cache_data') or {}
        if not isinstance(data_factory_cache, dict):
            raise AutoApiError(
                AUTO_API_BASE_ASSERTION_VERIFICATION_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED_CODE_CACHE_SCENARIO_ASSERTION_EXECUTION_FAILED)
        for key, value in data_factory_cache.items():
            test_setup.test_data.set_data_factory_cache(key, value)

        try:
            case_parameter = CaseParameter(
                test_setup,
                verify_parameter,
                api_info,
                test_env=test_env,
            )
            assertion_results, status, error_message = case_parameter.verify_all_assertions(response)
        finally:
            test_setup.close_db_connections()

        effective_results = [
            item for item in assertion_results
            if not item.group_name or item.source_type == 'assertion_group'
        ]
        passed_count = sum(item.status == StatusEnum.SUCCESS.value for item in effective_results)
        failed_count = len(effective_results) - passed_count
        return {
            'parameter_id': parameter.id,
            'passed': status == StatusEnum.SUCCESS.value,
            'status': status,
            'error_message': error_message,
            'result_count': len(effective_results),
            'passed_count': passed_count,
            'failed_count': failed_count,
            'source_test_time': result_data.get('test_time'),
            'assertions': [item.model_dump() for item in assertion_results],
        }

    @staticmethod
    def _validate_assertion_payload(assertions: dict):
        for field in ('ass_jsonpath', 'ass_sql', 'ass_general'):
            value = assertions.get(field)
            if value is not None and not isinstance(value, list):
                raise AutoApiError(AUTO_API_ASSERTION_VALUE_ARRAY_REQUIRED, value=(field,))
        json_all = assertions.get('ass_json_all')
        if json_all is not None and not isinstance(json_all, (dict, list)):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED)
        schema = assertions.get('ass_schema')
        if schema is not None and not isinstance(schema, dict):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_JSON_ASSERTION_FAILED_CODE_JSON_ASSERTION_FAILED)
        text_value = assertions.get('ass_text_all')
        if text_value is not None and not isinstance(text_value, str):
            raise AutoApiError(AUTO_API_BASE_ASSERTION_VERIFICATION_ASSERTION_FAILED_CODE_ASSERTION_FAILED)

    @staticmethod
    def _has_assertion(parameter, api_info) -> bool:
        return any([
            parameter.ass_json_all,
            parameter.ass_text_all,
            parameter.ass_jsonpath,
            getattr(parameter, 'ass_sql', None),
            parameter.ass_schema,
            parameter.ass_general,
        ])
