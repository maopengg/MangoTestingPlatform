# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_ui.models import PageSteps, PageStepsDetailed
from src.auto_test.auto_ui.service.test_case.test_case import TestCase
from src.auto_test.auto_ui.views.ui_page import PageSerializers
from src.enums.system_enum import ClientNameEnum
from src.enums.tools_enum import StatusEnum
from src.exceptions import MangoServerError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PageStepsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageSteps
        fields = '__all__'


class PageStepsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    page = PageSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = PageSteps
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'page',
            'module')
        return queryset


class PageStepsCRUD(ModelCRUD):
    model = PageSteps
    queryset = PageSteps.objects.all()
    serializer_class = PageStepsSerializersC
    serializer = PageStepsSerializers


class PageStepsViews(ViewSet):
    model = PageSteps
    serializer_class = PageStepsSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_steps_run(self, request: Request):
        """
        执行一条用例
        @param request:
        @return:
        """
        is_send = request.query_params.get("is_send", True)
        if is_send:
            is_send = bool(int(is_send))
        try:
            case_json = TestCase(
                request.user['id'],
                request.user['username'],
                request.GET.get("te"),
                is_send=is_send) \
                .test_steps(int(request.query_params.get("page_step_id")))
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0074, case_json.model_dump(), value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def get_page_steps_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        res = self.model.objects.filter(page=request.query_params.get('page_id')).values_list('id', 'name')
        return ResponseData.success(RESPONSE_MSG_0087, [{'key': _id, 'title': name} for _id, name in res])

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def copy_page_steps(self, request: Request):
        from src.auto_test.auto_ui.views.ui_page_steps_detailed import PageStepsDetailedSerializers
        page_id = request.data.get('page_id')
        page_obj = PageSteps.objects.get(id=page_id)
        page_obj = model_to_dict(page_obj)
        page_id = page_obj['id']
        page_obj['name'] = '(副本)' + page_obj['name']
        page_obj['type'] = StatusEnum.FAIL.value
        del page_obj['id']
        serializer = self.serializer_class(data=page_obj)
        if serializer.is_valid():
            serializer.save()
            ui_page_steps_detailed_obj = PageStepsDetailed.objects.filter(page_step=page_id)
            for i in ui_page_steps_detailed_obj:
                page_steps_detailed = model_to_dict(i)
                del page_steps_detailed['id']
                page_steps_detailed['page_step'] = serializer.data['id']
                ui_page_steps_serializer = PageStepsDetailedSerializers(data=page_steps_detailed)
                if ui_page_steps_serializer.is_valid():
                    ui_page_steps_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0089, ui_page_steps_serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0088, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0089, serializer.errors)
