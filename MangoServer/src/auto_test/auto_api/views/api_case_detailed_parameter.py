# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏

from mangotools.data_processor import JsonTool
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiInfo, ApiCaseDetailedParameter
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class ApiCaseDetailedParameterSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseDetailedParameter
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset


class ApiCaseDetailedParameterCRUD(ModelCRUD):
    model = ApiCaseDetailedParameter
    queryset = ApiCaseDetailedParameter.objects.all()
    serializer_class = ApiCaseDetailedParameterSerializers
    serializer = ApiCaseDetailedParameterSerializers

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
        return ResponseData.success(RESPONSE_MSG_0024, return_data)


class ApiCaseDetailedParameterViews(ViewSet):
    model = ApiCaseDetailedParameter
    serializer_class = ApiCaseDetailedParameterSerializers

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def post_test_jsonpath(self, request: Request):
        jsonpath = request.data.get('jsonpath')
        response_json = request.data.get('response_json')
        if isinstance(jsonpath, str):
            key = None
            value = jsonpath
        else:
            key = jsonpath.get('key')
            value = jsonpath.get('value')
        if key and key.startswith('$.'):
            key = JsonTool.get_json_path_value(response_json, key)
        value = JsonTool.get_json_path_value(response_json, value)
        return ResponseData.success(RESPONSE_MSG_0135, data={'key': key, 'value': value})
