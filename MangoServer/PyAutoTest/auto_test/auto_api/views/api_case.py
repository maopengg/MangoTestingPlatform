# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏

from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.api_call.test_case import TestCase
from PyAutoTest.auto_test.auto_api.service.api_import.automatic_parsing_interface import ApiParameter
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.add_tasks import AddTasks
from PyAutoTest.auto_test.auto_system.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.api_model import ApiCaseResultModel
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class ApiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    case_people = UserSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
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
    @error_response('api')
    def api_test_case(self, request: Request):
        api_case_run = TestCase(
            user_id=request.user.get('id'),
            test_env=request.query_params.get('test_env'),
        )
        test_result: ApiCaseResultModel = api_case_run.test_case(
            request.query_params.get('case_id'),
            request.query_params.get('case_sort')

        )
        if StatusEnum.SUCCESS.value != test_result.status:
            return ResponseData.fail((300, test_result.error_message), test_result.model_dump())
        return ResponseData.success(RESPONSE_MSG_0111, test_result.model_dump())

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_test_case_batch(self, request: Request):
        case_id_list = request.data.get('case_id_list')
        case_project = None
        for i in case_id_list:
            if case_project is None:
                case_project = ApiCase.objects.get(id=i).project_product.id
            else:
                if case_project != ApiCase.objects.get(id=i).project_product.id:
                    return ResponseData.fail(RESPONSE_MSG_0128, )
        add_tasks = AddTasks(
            project=case_project,
            test_env=request.data.get('test_env'),
            is_notice=StatusEnum.FAIL.value,
            user_id=request.user['id'],
            _type=AutoTestTypeEnum.API.value,
        )
        add_tasks.add_test_suite_details(case_id_list)
        return ResponseData.success(RESPONSE_MSG_0111)

    @action(methods=['get'], detail=False)
    @error_response('api')
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
                log.api.error(f"错误信息：{str(serializer.errors)}"
                              f"错误数据：{i}")
                res.append(False)
        if False in res:
            return ResponseData.fail(RESPONSE_MSG_0006)
        return ResponseData.success(RESPONSE_MSG_0007, )

    @action(methods=['POST'], detail=False)
    @error_response('api')
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
