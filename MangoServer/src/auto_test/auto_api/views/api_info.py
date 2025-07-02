# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import json
from urllib.parse import urlparse, parse_qs
from curlparser import parse
from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from src.enums.api_enum import MethodEnum
from src.auto_test.auto_api.models import ApiInfo
from src.auto_test.auto_api.service.test_case.test_api_info import TestApiInfo
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.tools_enum import StatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class ApiInfoSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiInfo
        fields = '__all__'


class ApiInfoSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = ApiInfo
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module')
        return queryset


class ApiInfoCRUD(ModelCRUD):
    model = ApiInfo
    queryset = ApiInfo.objects.all()
    serializer_class = ApiInfoSerializersC
    serializer = ApiInfoSerializers


class ApiInfoViews(ViewSet):
    model = ApiInfo
    serializer_class = ApiInfoSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_api_info_run(self, request: Request):
        api_info_id = request.query_params.get('id')
        test_env = request.query_params.get('test_env')
        api_info_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]

        if not api_info_id and api_info_list:
            api_info_res_list = []
            for api_info_id in api_info_list:
                api_info_res: dict = TestApiInfo(
                    request.user['id'], test_env, ).api_info_run(api_info_id)
                api_info_res_list.append(api_info_res)
            return ResponseData.success(RESPONSE_MSG_0072, api_info_res_list)
        else:
            api_info_res: dict = TestApiInfo(request.user['id'], test_env, ).api_info_run(api_info_id)
            return ResponseData.success(RESPONSE_MSG_0072, api_info_res)

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_api_name(self, request: Request):
        """
        获取用户名称
        :param request:
        :return:
        """
        res = self.model.objects.filter(module=request.query_params.get('module_id')).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0071, data)

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_api_info_type(self, request: Request):
        _type = request.data.get('type')
        id_list = request.data.get('id_list')
        for i in id_list:
            api_info_obj = self.model.objects.get(id=i)
            api_info_obj.type = _type
            api_info_obj.save()
        return ResponseData.success(RESPONSE_MSG_0070, )

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def copy_api_info(self, request: Request):
        api_info = self.model.objects.get(id=request.data.get('id'))
        api_info = model_to_dict(api_info)
        api_info['status'] = StatusEnum.FAIL.value
        api_info['name'] = '(副本)' + api_info.get('name')
        del api_info['id']
        serializer = self.serializer_class(data=api_info)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0069, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0068, serializer.errors)

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def import_api(self, request: Request):
        parsed = parse(request.data.get('curl_command'))
        url_components = urlparse(parsed.url)
        path = url_components.path
        result = {
            'name': request.data.get('name'),
            'module': request.data.get('module'),
            'project_product': request.data.get('project_product'),
            'type': request.data.get('type'),
            'url': path,
            'method': MethodEnum.get_key(parsed.method),
            # 'headers': dict(parsed.header),
        }
        query_params = parse_qs(url_components.query)
        params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        if params:
            result['params'] = json.dumps(params)
        if parsed.json and parsed.data:
            result['json'] = json.dumps(parsed.json)
        elif parsed.json is None and parsed.data:
            result['data'] = json.dumps(parsed.data)
        elif parsed.json and parsed.data is None:
            result['json'] = json.dumps(parsed.json)
        data = ApiInfoCRUD.inside_post(result)
        return ResponseData.success(RESPONSE_MSG_0069, data=data)
