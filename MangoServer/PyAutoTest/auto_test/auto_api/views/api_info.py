# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import argparse
import logging
import shlex

from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_api.service.test_execution.api_info_run import ApiInfoRun
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.project_module import ProjectModuleSerializers
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
    project = ProjectSerializers(read_only=True)
    module_name = ProjectModuleSerializers(read_only=True)

    class Meta:
        model = ApiInfo
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'module_name')
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
        project_id = request.query_params.get('project_id')
        api_info_id = request.query_params.get('id')
        test_obj_id = request.query_params.get('test_obj_id')
        try:
            api_info_res: ResponseDataModel = ApiInfoRun(project_id, test_obj_id).api_info_run(api_info_id)
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
        res = self.model.objects.filter(module_name=request.query_params.get('module_id')).values_list('id', 'name')
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

    # data = ImportApi().curl_import(request.data.get('data'))
    # import subprocess
    #
    # data = subprocess.run(request.data.get('data'), shell=True)

    @action(methods=['POST'], detail=False)
    def import_api(self, request: Request):
        data = request.data.get('data')
        import re

        # 使用正则表达式匹配URL
        # urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        # 编译一个正则表达式模式，匹配 fetch(...) 中的内容
        pattern = re.compile(r'fetch\((.*?)\);')

        # 使用 findall 方法查找所有匹配的内容
        matches = pattern.findall(data)

        # 将匹配的内容转换为元组
        result_tuple = tuple(matches)

        print(result_tuple)
        return ResponseData.success(RESPONSE_MSG_0069)


