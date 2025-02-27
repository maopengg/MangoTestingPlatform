# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_ui.models import UiCase
from src.auto_test.auto_ui.service.test_case.test_case import TestCase
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.system_enum import ClientNameEnum
from src.enums.tools_enum import StatusEnum, AutoTestTypeEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class UiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'


class UiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'case_people')
        return queryset


class UiCaseCRUD(ModelCRUD):
    model = UiCase
    queryset = UiCase.objects.all()
    serializer_class = UiCaseSerializersC
    serializer = UiCaseSerializers


class UiCaseViews(ViewSet):
    model = UiCase
    serializer_class = UiCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_test_case(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        case_model = TestCase(
            request.user['id'],
            request.user['username'],
            request.query_params.get("test_env"),
            is_send=True
        ).test_case(int(request.query_params.get("case_id")))
        return ResponseData.success(RESPONSE_MSG_0074, data=case_model.model_dump(),
                                    value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ui_test_case_batch(self, request: Request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        case_id_list = request.data.get('case_id_list')
        case_project_product = None
        case_project = None
        for i in case_id_list:
            if case_project is None:
                case_project_product = UiCase.objects.get(id=i).project_product.id
                case_project = UiCase.objects.get(id=i).project_product.project.id
            else:
                if case_project != UiCase.objects.get(id=i).project_product.project.id:
                    return ResponseData.fail(RESPONSE_MSG_0128, )
        add_tasks = AddTasks(
            project_product=case_project_product,
            test_env=request.data.get("test_env"),
            is_notice=StatusEnum.FAIL.value,
            user_id=request.user['id'],
        )
        add_tasks.add_test_suite_details(case_id_list, AutoTestTypeEnum.UI.value)
        return ResponseData.success(RESPONSE_MSG_0074, value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def cody_case(self, request: Request):
        from src.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedSerializers
        from src.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailed
        case_id = request.data.get('case_id')
        case_obj = UiCase.objects.get(id=case_id)
        case_obj = model_to_dict(case_obj)
        case_id = case_obj['id']
        case_obj['name'] = '(副本)' + case_obj['name']
        case_obj['status'] = StatusEnum.FAIL.value
        del case_obj['id']
        serializer = self.serializer_class(data=case_obj)
        if serializer.is_valid():
            serializer.save()
            ui_case_steps_detailed_obj = UiCaseStepsDetailed.objects.filter(case=case_id)
            for i in ui_case_steps_detailed_obj:
                case_steps_detailed = model_to_dict(i)
                del case_steps_detailed['id']
                case_steps_detailed['case'] = serializer.data['id']
                ui_case_steps_serializer = UiCaseStepsDetailedSerializers(data=case_steps_detailed)
                if ui_case_steps_serializer.is_valid():
                    ui_case_steps_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0075, ui_case_steps_serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0073, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0075, serializer.errors)
