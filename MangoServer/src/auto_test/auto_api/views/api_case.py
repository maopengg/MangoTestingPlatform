# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
from django.db import transaction

from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiCase
from src.auto_test.auto_api.service.api_import.automatic_parsing_interface import ApiParameter
from src.auto_test.auto_api.service.test_case.test_case import TestCase
from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.models.api_model import ApiCaseResultModel
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


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
        case_project_product = None
        case_project = None
        for i in case_id_list:
            if case_project is None:
                case_project_product = ApiCase.objects.get(id=i).project_product.id
                case_project = ApiCase.objects.get(id=i).project_product.project.id
            else:
                if case_project != ApiCase.objects.get(id=i).project_product.project.id:
                    return ResponseData.fail(RESPONSE_MSG_0128, )
        add_tasks = AddTasks(
            project_product=case_project_product,
            test_env=request.data.get('test_env'),
            is_notice=StatusEnum.FAIL.value,
            user_id=request.user['id'],
        )
        for case_id in case_id_list:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.API)
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
    @transaction.atomic
    def copy_case(self, request: Request):
        from src.auto_test.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
        from src.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
        from src.auto_test.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
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
                res_case_de = ApiCaseDetailedCRUD.inside_post(api_case_detailed)
                for p in ApiCaseDetailedParameter.objects.filter(case_detailed_id=i.id):
                    parameter = model_to_dict(p)
                    del parameter['id']
                    parameter['case_detailed'] = res_case_de.get('id')
                    ApiCaseDetailedParameterCRUD.inside_post(parameter)
            return ResponseData.success(RESPONSE_MSG_0009, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0008, serializer.errors)

    @action(methods=['GET'], detail=False)
    @error_response('api')
    def case_name(self, request: Request):
        res = self.model.objects \
            .filter(module_id=request.query_params.get('module_id')) \
            .values_list('id', 'name')
        return ResponseData.fail(RESPONSE_MSG_0023, [{'key': _id, 'title': name} for _id, name in res])
