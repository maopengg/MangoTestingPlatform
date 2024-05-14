# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPageSteps, UiPageStepsDetailed
from PyAutoTest.auto_test.auto_ui.service.ui_test_run import UiTestRun
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.project_product import ProjectProductSerializersC
from PyAutoTest.enums.tools_enum import StatusEnum, ClientNameEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class UiPageStepsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPageSteps
        fields = '__all__'


class UiPageStepsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    page = UiPageSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = UiPageSteps
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'page',
            'module')
        return queryset


class UiPageStepsCRUD(ModelCRUD):
    model = UiPageSteps
    queryset = UiPageSteps.objects.all()
    serializer_class = UiPageStepsSerializersC
    serializer = UiPageStepsSerializers


class UiPageStepsViews(ViewSet):
    model = UiPageSteps
    serializer_class = UiPageStepsSerializers

    @action(methods=['get'], detail=False)
    def ui_steps_run(self, request: Request):
        """
        执行一条用例
        @param request:
        @return:
        """
        try:
            case_json = UiTestRun(request.user['id'], request.GET.get("te"))\
                .steps(steps_id=int(request.GET.get("page_step_id")))
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0074, case_json.dict(), value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['put'], detail=False)
    def put_type(self, request: Request):
        for i in request.data.get('id'):
            case = self.model.objects.get(id=i)
            case.type = 0 if case.type == 1 else 1 if not case.type else 1
            case.save()
        return ResponseData.success(RESPONSE_MSG_0085, )

    @action(methods=['get'], detail=False)
    def get_case_name(self, request: Request):
        """
         获取所有用例id和名称
         :param request:
         :return:
         """
        res = self.model.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0086, data)

    @action(methods=['GET'], detail=False)
    def get_page_steps_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        res = self.model.objects.filter(page=request.query_params.get('page_id')).values_list('id', 'name')
        return ResponseData.success(RESPONSE_MSG_0087, [{'key': _id, 'title': name} for _id, name in res])

    @action(methods=['POST'], detail=False)
    def copy_page_steps(self, request: Request):
        from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import UiPageStepsDetailedSerializers
        page_id = request.data.get('page_id')
        page_obj = UiPageSteps.objects.get(id=page_id)
        page_obj = model_to_dict(page_obj)
        page_id = page_obj['id']
        page_obj['name'] = '(副本)' + page_obj['name']
        page_obj['type'] = StatusEnum.FAIL.value
        del page_obj['id']
        serializer = self.serializer_class(data=page_obj)
        if serializer.is_valid():
            serializer.save()
            ui_page_steps_detailed_obj = UiPageStepsDetailed.objects.filter(page_step=page_id)
            for i in ui_page_steps_detailed_obj:
                page_steps_detailed = model_to_dict(i)
                del page_steps_detailed['id']
                page_steps_detailed['page_step'] = serializer.data['id']
                ui_page_steps_serializer = UiPageStepsDetailedSerializers(data=page_steps_detailed)
                if ui_page_steps_serializer.is_valid():
                    ui_page_steps_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0089, ui_page_steps_serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0088, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0089, serializer.errors)
