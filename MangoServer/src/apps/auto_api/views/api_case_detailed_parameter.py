# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import re

from django.db import transaction
from django.forms import model_to_dict
from mangotools.data_processor import JsonTool
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiInfo, ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.schemas.case_schema import (
    ApiGeneralAssertionItem,
    ApiJsonPathAssertionItem,
    ApiKeyValueItem,
    ApiSqlAssertionItem,
    validate_file_payload,
    validate_int_list,
    validate_json_object,
    validate_model_list,
)
from src.common.exceptions import ApiError, ERROR_MSG_0017
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *
from genson import SchemaBuilder


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

    def validate_file(self, value):
        return validate_file_payload(value, 'file')

    def validate_front_sql(self, value):
        return validate_model_list(value, ApiKeyValueItem, '前置sql')

    def validate_ass_general(self, value):
        return validate_model_list(value, ApiGeneralAssertionItem, '通用断言')

    def validate_ass_sql(self, value):
        return validate_model_list(value, ApiSqlAssertionItem, 'SQL断言')

    def validate_ass_json_all(self, value):
        return validate_json_object(value, '响应JSON全匹配断言', allow_list=True)

    def validate_ass_jsonpath(self, value):
        return validate_model_list(value, ApiJsonPathAssertionItem, '响应jsonpath断言')

    def validate_ass_schema(self, value):
        return validate_json_object(value, 'schema配置')

    def validate_posterior_sql(self, value):
        return validate_model_list(value, ApiKeyValueItem, '后置sql')

    def validate_posterior_response(self, value):
        return validate_model_list(value, ApiKeyValueItem, '后置响应处理')

    def validate_posterior_response_text(self, value):
        return validate_model_list(value, ApiKeyValueItem, '后置响应文本处理')

    def validate_posterior_file(self, value):
        return validate_model_list(value, ApiKeyValueItem, '文件下载', allow_none=True, allow_empty_dict=True)

    def validate_result_data(self, value):
        return validate_json_object(value, '最近一次执行结果')


class ApiCaseDetailedParameterCRUD(ModelCRUD):
    model = ApiCaseDetailedParameter
    queryset = ApiCaseDetailedParameter.objects.all()
    serializer_class = ApiCaseDetailedParameterSerializers
    serializer = ApiCaseDetailedParameterSerializers

    @staticmethod
    def refresh_case_flow(case_detailed_id):
        case_detailed = ApiCaseDetailed.objects.filter(id=case_detailed_id).first()
        if not case_detailed:
            return
        from src.apps.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
        ApiCaseDetailedCRUD().callback(case_detailed.case_id)

    @error_response('api')
    def post(self, request: Request):
        data = request.data
        api_info_obj = ApiInfo.objects.get(id=request.data.get('api_info'))
        data['url'] = api_info_obj.url
        data['params'] = api_info_obj.params
        data['data'] = api_info_obj.data
        data['json'] = api_info_obj.json
        data['file'] = api_info_obj.file
        return_data = self.inside_post(data)
        self.refresh_case_flow(return_data.get('case_detailed'))
        return ResponseData.success(RESPONSE_MSG_0024, return_data)

    @error_response('api')
    def put(self, request: Request):
        parameter = self.model.objects.get(id=request.data.get('id'))
        case_detailed_id = parameter.case_detailed_id
        response = super().put(request)
        self.refresh_case_flow(case_detailed_id)
        return response

    @error_response('api')
    def delete(self, request: Request):
        _id = request.query_params.get('id')
        id_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]
        case_detailed_ids = set()
        if _id:
            parameter = self.model.objects.filter(id=_id).first()
            if parameter:
                case_detailed_ids.add(parameter.case_detailed_id)
        if id_list:
            case_detailed_ids.update(
                self.model.objects.filter(id__in=id_list).values_list('case_detailed_id', flat=True)
            )
        response = super().delete(request)
        for case_detailed_id in case_detailed_ids:
            self.refresh_case_flow(case_detailed_id)
        return response


class ApiCaseDetailedParameterViews(ViewSet):
    model = ApiCaseDetailedParameter
    serializer_class = ApiCaseDetailedParameterSerializers

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
            if key and key.startswith('$.'):
                key = JsonTool.get_json_path_value(response, key)
            value = JsonTool.get_json_path_value(response, value)
            return ResponseData.success(RESPONSE_MSG_0135, data={'key': key, 'value': value})
        else:
            value = re.findall(value, response)
            if len(value) <= 0:
                raise ApiError(*ERROR_MSG_0017)
            return ResponseData.success(RESPONSE_MSG_0135, data={'key': key, 'value': value})

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_auto_schema(self, request):
        model = self.model.objects.get(id=request.data.get('id'))
        response = model.result_data.get('response', {}).get('json')
        if response is None:
            return ResponseData.fail(RESPONSE_MSG_0156)
        builder = SchemaBuilder()
        builder.add_object(response)
        schema = builder.to_schema()
        model.ass_schema = schema
        model.save()
        return ResponseData.success(RESPONSE_MSG_0157, data=schema)

    @action(methods=['post'], detail=False)
    @error_response('api')
    @transaction.atomic
    def copy_parameter(self, request: Request):
        from src.apps.auto_data_factory.models import DataFactoryCaseConfig
        from src.apps.auto_data_factory.views.case_config import DataFactoryCaseConfigCRUD
        from src.common.enums.data_factory_enum import DataFactoryCaseSourceTypeEnum

        source_id = request.data.get('id')
        source = self.model.objects.get(id=source_id)
        parameter = model_to_dict(source)
        del parameter['id']
        parameter['name'] = request.data.get('name') or f"(副本){source.name}"
        parameter['error_retry'] = request.data.get('error_retry')
        parameter['retry_interval'] = request.data.get('retry_interval')
        parameter['status'] = 2
        parameter['result_data'] = None
        new_parameter = ApiCaseDetailedParameterCRUD.inside_post(parameter)

        for factory_config in DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                source_id=source_id,
        ):
            data_factory = model_to_dict(factory_config)
            del data_factory['id']
            data_factory['source_type'] = DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value
            data_factory['source_id'] = new_parameter.get('id')
            DataFactoryCaseConfigCRUD.inside_post(data_factory)

        ApiCaseDetailedParameterCRUD.refresh_case_flow(source.case_detailed_id)
        return ResponseData.success(RESPONSE_MSG_0009, new_parameter)
