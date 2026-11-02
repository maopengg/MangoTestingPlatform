# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import re

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation import (
    ApiCaseDetailedParameterSerializers,
)
from src.apps.auto_api.exceptions import (
    AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_REQUIRED,
    AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_EXECUTION_FAILED,
    AutoApiError,
    API_POST_REGEX_RESPONSE_EMPTY,
    API_POST_REGEX_NO_MATCH,
    API_POST_REGEX_INVALID,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import (
    merge_scenario_protocol_config,
)
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseParameterMutationService
from src.apps.auto_api.services.api_case.parameter_copy import ApiCaseParameterCopyService
from src.apps.auto_api.services.api_case.schema import ApiCaseScenarioSchemaService
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.services.base.assertion_verification import ApiAssertionVerificationService
from src.common.decorators.error_response import error_response
from src.common.responses.json_response import ensure_jsonpath_source, extract_jsonpath_value
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0009,
    RESPONSE_MSG_0024,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0135,
    RESPONSE_MSG_0157,
    RESPONSE_MSG_0210,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, with_update_user


class ApiCaseDetailedParameterCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiCaseDetailedParameter
    queryset = ApiCaseDetailedParameter.objects.all()
    serializer_class = ApiCaseDetailedParameterSerializers
    serializer = ApiCaseDetailedParameterSerializers
    page_permission_key = 'api.case'
    deprecated_fields = {
        'data',
        'json',
        'file',
        'protocol_type',
        'body_type',
        'mcp_config',
        'grpc_config',
        'protocol_expectation',
        'result_data',
    }

    @classmethod
    def clean_deprecated_fields(cls, data: dict) -> dict:
        cleaned = data.copy()
        if any(field in cleaned for field in ('body_config', 'mcp_config', 'grpc_config', 'protocol_expectation')):
            cleaned['body_config'] = merge_scenario_protocol_config(
                cleaned.get('body_config'),
                cleaned.get('mcp_config'),
                cleaned.get('grpc_config'),
                cleaned.get('protocol_expectation'),
            )
        for field in cls.deprecated_fields:
            cleaned.pop(field, None)
        return cleaned

    @classmethod
    def inside_post(cls, data: dict, *, record_config: bool = True) -> dict:
        return ApiCaseParameterMutationService.create(
            data,
            record_config=record_config,
            source="page",
        )

    @classmethod
    def inside_put(cls, _id: int, data: dict, *, record_config: bool = True) -> dict:
        return ApiCaseParameterMutationService.update(
            _id,
            data,
            record_config=record_config,
            source="page",
        )

    @staticmethod
    def refresh_case_flow(case_detailed_id):
        case_detailed = ApiCaseDetailed.objects.filter(id=case_detailed_id).first()
        if not case_detailed:
            return
        from src.apps.auto_api.api.views.api_case_detailed import ApiCaseDetailedCRUD
        ApiCaseDetailedCRUD().callback(case_detailed.case_id)

    @error_response('api')
    def post(self, request: Request):
        data = request.data.copy()
        data.pop('api_info', None)
        case_detailed = ApiCaseDetailed.objects.get(id=data.get('case_detailed'))
        api_info_obj = ApiCaseStepService.resolve_step_api_runtime(case_detailed, allow_draft=True)
        data['params'] = api_info_obj.params
        data['body_config'] = api_info_obj.body_config
        data['sse_config'] = api_info_obj.sse_config
        return_data = ApiCaseAggregateMutationService.mutate(
            case_detailed.case_id,
            action='create_parameter',
            operation=lambda _: self.inside_post(
                with_update_user(data, request),
                record_config=False,
            ),
            operator_id=self.get_operator_id(request),
            source='page',
        )
        return ResponseData.success(RESPONSE_MSG_0024, return_data)

    @error_response('api')
    def put(self, request: Request):
        parameter = self.model.objects.get(id=request.data.get('id'))
        return_data = ApiCaseAggregateMutationService.mutate(
            parameter.case_detailed.case_id,
            action='update_parameter',
            operation=lambda _: self.inside_put(
                parameter.id,
                with_update_user(request.data.copy(), request),
                record_config=False,
            ),
            operator_id=self.get_operator_id(request),
            source='page',
        )
        return ResponseData.success(RESPONSE_MSG_0082, return_data)

    @error_response('api')
    def delete(self, request: Request):
        _id = request.query_params.get('id')
        id_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]
        if _id:
            id_list.append(int(_id))
        parameters = list(
            self.model.objects.select_related('case_detailed__case').filter(
                id__in=set(id_list)
            )
        )
        if len(parameters) != len(set(id_list)):
            return ResponseData.fail(RESPONSE_MSG_0029)
        from src.apps.auto_api.api.views.api_case import ApiCaseCRUD
        if any(
                not ApiCaseCRUD().has_instance_data_scope_permission(
                    request,
                    parameter.case_detailed.case,
                )
                for parameter in parameters
        ):
            return ResponseData.fail(RESPONSE_MSG_0210)
        ApiCaseStepService.delete_parameters(
            id_list,
            operator_id=self.get_operator_id(request),
            source='page',
        )
        return ResponseData.success(RESPONSE_MSG_0005)


class ApiCaseDetailedParameterViews(ViewSet):
    model = ApiCaseDetailedParameter
    serializer_class = ApiCaseDetailedParameterSerializers

    @action(methods=['post'], detail=False)
    @error_response('api')
    def verify_assertions(self, request: Request):
        parameter_id = request.data.get('id')
        if parameter_id in [None, '']:
            raise AutoApiError(AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_REQUIRED)
        test_env = request.data.get('test_env', 0)
        try:
            parameter_id = int(parameter_id)
            test_env = int(test_env)
        except (TypeError, ValueError) as error:
            raise AutoApiError(
                AUTO_API_API_CASE_DETAILED_PARAMETER_SCENARIO_ASSERTION_PARAMETER_EXECUTION_FAILED) from error
        result = ApiAssertionVerificationService.verify(
            parameter_id,
            request.data.get('assertions') or {},
            test_env=test_env,
        )
        return ResponseData.success((200, '断言验证完成'), result)

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_extract_response_after(self, request: Request):
        expression = request.data.get('expression')
        _type = request.data.get('type')
        response = request.data.get('response')
        if isinstance(expression, str):
            key = None
            value = expression
        else:
            key = expression.get('key')
            value = expression.get('value')
        if _type == 'jsonpath':
            ensure_jsonpath_source(response)
            if key and key.startswith('$.'):
                key = extract_jsonpath_value(
                    response,
                    key,
                    operation='后置JSONPath测试缓存Key提取',
                )
            value = extract_jsonpath_value(
                response,
                value,
                operation='后置JSONPath测试提取',
                cache_key=key,
            )
            return ResponseData.success(RESPONSE_MSG_0135, data={'key': key, 'value': value})
        else:
            regex_expression = value
            cache_key = key or '未设置'
            if response is None:
                raise AutoApiError(API_POST_REGEX_RESPONSE_EMPTY, value=(cache_key, regex_expression))
            try:
                value = re.findall(regex_expression, response)
            except re.error as error:
                raise AutoApiError(API_POST_REGEX_INVALID,
                                   value=(cache_key, regex_expression, str(error)),
                                   ) from error
            if len(value) <= 0:
                raise AutoApiError(API_POST_REGEX_NO_MATCH,
                                   value=(cache_key, regex_expression, len(response)),
                                   )
            return ResponseData.success(RESPONSE_MSG_0135, data={'key': key, 'value': value})

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_auto_schema(self, request):
        result = ApiCaseScenarioSchemaService.generate(
            request.data.get('id'),
            operator_id=ApiCaseDetailedParameterCRUD.get_operator_id(request),
            source='page',
        )
        return ResponseData.success(RESPONSE_MSG_0157, data=result['ass_schema'])

    @action(methods=['post'], detail=False)
    @error_response('api')
    def copy_parameter(self, request: Request):
        source_id = request.data.get('id')
        new_parameter = ApiCaseParameterCopyService.copy(
            int(source_id),
            dict(request.data),
            operator_id=ApiCaseDetailedParameterCRUD.get_operator_id(request),
        )
        return ResponseData.success(
            RESPONSE_MSG_0009,
            self.serializer_class(instance=new_parameter).data,
        )
