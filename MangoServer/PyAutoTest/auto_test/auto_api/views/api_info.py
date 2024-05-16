# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import logging

from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.test_execution.info_run import ApiInfoRun
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.project_product import ProjectProductSerializersC
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.models.apimodel import ResponseDataModel
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('api')


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
    def get_api_info_run(self, request: Request):
        api_info_id = request.query_params.get('id')
        test_obj_id = request.query_params.get('test_obj_id')
        api_info_list = [int(id_str) for id_str in request.query_params.getlist('id[]')]

        try:
            if not api_info_id and api_info_list:
                api_info_res_list = []
                for api_info_id in api_info_list:
                    api_info_res: ResponseDataModel = ApiInfoRun(test_obj_id, api_info_id).api_info_run()
                    api_info_res_list.append(api_info_res.model_dump_json())
                return ResponseData.success(RESPONSE_MSG_0072, api_info_res_list)
            else:
                api_info_res: ResponseDataModel = ApiInfoRun(test_obj_id, api_info_id).api_info_run()
                return ResponseData.success(RESPONSE_MSG_0072, api_info_res.dict())
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg), )

    @action(methods=['get'], detail=False)
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
    def put_api_info_type(self, request: Request):
        _type = request.data.get('type')
        id_list = request.data.get('id_list')
        for i in id_list:
            api_info_obj = self.model.objects.get(id=i)
            api_info_obj.type = _type
            api_info_obj.save()
        return ResponseData.success(RESPONSE_MSG_0070, )

    @action(methods=['POST'], detail=False)
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

    # import subprocess
    #
    # data = subprocess.run(request.data.get('data'), shell=True)

    @action(methods=['POST'], detail=False)
    def import_api(self, request: Request):
        data = f"""
        {request.data.get('data')}
        """
        d = """
        curl 'https://cdxppre.zalldata.cn/backend/api-user/user/info' \
  -H 'authority: cdxppre.zalldata.cn' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: zh-CN,zh;q=0.9,en;q=0.8' \
  -H 'authorization: Bearer 9f02351c-9382-4d0c-99aa-3aead4401cef' \
  -H 'cache-control: no-cache' \
  -H 'currentproject: precheck' \
  -H 'pragma: no-cache' \
  -H 'referer: https://cdxppre.zalldata.cn/operate/userJourneyInfo?id=2377&type=look&status=2&hasStart=0&projectName=precheck' \
  -H 'sec-ch-ua: "Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'service: zall' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' \
  -H 'userid: 201' \
  -H 'x-nonce: JcD7zXMl4xEk6YUr6gzll1YLfuZtsjmu' \
  -H 'x-sign: 812f6a242139173822e8e5451bbcca83e36c93f70898dd6bc98b73f81747c1f6' \
  -H 'x-time: 1713507951432'
        """
        assert data == d
        import argparse
        import shlex
        parser = argparse.ArgumentParser()
        parser.add_argument('command')
        parser.add_argument('url')
        parser.add_argument('-d', '--data')
        parser.add_argument('-b', '--data-binary', '--data-raw', default=None)
        parser.add_argument('-X', default='')
        parser.add_argument('-H', '--header', action='append', default=[])
        parser.add_argument('--compressed', action='store_true')
        parser.add_argument('-k', '--insecure', action='store_true')
        parser.add_argument('--user', '-u', default=())
        parser.add_argument('-i', '--include', action='store_true')
        parser.add_argument('-s', '--silent', action='store_true')
        tokens = shlex.split(data)
        parsed_args = parser.parse_args(tokens)
        return ResponseData.success(RESPONSE_MSG_0069)
