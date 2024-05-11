# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import logging

from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.automatic_parsing_interface import ApiParameter
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('api')


class ApiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'case_people',
            'module')
        return queryset


class ApiCaseCRUD(ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializersC
    serializer = ApiCaseSerializers


class ApiCaseViews(ViewSet):
    model = ApiCase
    serializer_class = ApiCaseSerializers

    @action(methods=['get'], detail=False)
    def api_case_run(self, request: Request):
        from PyAutoTest.auto_test.auto_api.service.test_execution.api_test_run import ApiTestRun
        case_id = request.query_params.get('case_id')
        test_obj_id = request.query_params.get('test_obj_id')
        case_sort = request.query_params.get('case_sort')
        try:
            api_case_run = ApiTestRun(test_obj_id, case_sort, user_obj=request.user)
            test_result: dict = api_case_run.run_one_case(case_id)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg), )
        if StatusEnum.FAIL.value == test_result['status']:
            return ResponseData.fail((300, test_result['error_message']), test_result)
        return ResponseData.success(RESPONSE_MSG_0111, test_result)

    @action(methods=['post'], detail=False)
    def api_case_batch_run(self, request: Request):
        from PyAutoTest.auto_test.auto_api.service.test_execution.api_test_run import ApiTestRun
        case_id_list = request.data.get('case_id_list')
        test_obj_id = request.data.get('test_obj_id')
        try:
            api_case_run = ApiTestRun(test_obj_id, user_obj=request.user)
            test_result: dict = api_case_run.case_batch(case_id_list)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg), )
        return ResponseData.success(RESPONSE_MSG_0111, test_result)

    @action(methods=['get'], detail=False)
    def api_synchronous_interface(self, request: Request):
        """
        同步接口
        @param request:
        @return:
        """
        host = request.GET.get('host')
        project_id = request.GET.get('project_id')
        case_list = ApiParameter(host, project_id).get_stage_api()
        res = []
        for i in case_list:
            serializer = self.serializer_class(data=i)
            if serializer.is_valid():
                serializer.save()
                res.append(True)
            else:
                log.error(f"错误信息：{str(serializer.errors)}"
                          f"错误数据：{i}")
                res.append(False)
        if False in res:
            return ResponseData.fail(RESPONSE_MSG_0006)
        return ResponseData.success(RESPONSE_MSG_0007, )

    @action(methods=['POST'], detail=False)
    def copy_case(self, request: Request):
        from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed
        from PyAutoTest.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedSerializers
        case_id = request.data.get('case_id')
        case_obj = ApiCase.objects.get(id=case_id)
        case_obj = model_to_dict(case_obj)
        case_id = case_obj['id']
        case_obj['status'] = StatusEnum.FAIL.value
        case_obj['name'] = '(副本)' + case_obj.get('name')
        del case_obj['id']
        serializer = self.serializer_class(data=case_obj)
        if serializer.is_valid():
            serializer.save()
            api_case_detailed_obj = ApiCaseDetailed.objects.filter(case=case_id)
            for i in api_case_detailed_obj:
                api_case_detailed = model_to_dict(i)
                del api_case_detailed['id']
                api_case_detailed['case'] = serializer.data['id']
                ui_case_steps_serializer = ApiCaseDetailedSerializers(data=api_case_detailed)
                if ui_case_steps_serializer.is_valid():
                    ui_case_steps_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0008)
            return ResponseData.success(RESPONSE_MSG_0009, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0008, serializer.errors)
