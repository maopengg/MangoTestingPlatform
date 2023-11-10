# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.data_producer.run_api import RunApi
from PyAutoTest.auto_test.auto_ui.models import UiPageSteps
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class UiPageStepsSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPageSteps
        fields = '__all__'


class UiPageStepsSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    page = UiPageSerializers(read_only=True)

    class Meta:
        model = UiPageSteps
        fields = '__all__'


class UiPageStepsQuery(ModelQuery):
    """
    条件查
    """
    model = UiPageSteps
    serializer_class = UiPageStepsSerializersC


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

        case_json, res = RunApi(request.user).steps(steps_id=int(request.GET.get("page_step_id")),
                                                    test_obj=request.GET.get("te"))
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json.dict())
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', case_json.dict())

    @action(methods=['put'], detail=False)
    def put_type(self, request: Request):
        ser = []
        data = []
        for i in eval(request.data.get('id')):
            case = self.model.objects.get(pk=i)
            serializer = self.serializer_class(instance=case,
                                               data={'type': request.data.get('type'),
                                                     'name': case.name})
            if serializer.is_valid():
                serializer.save()
            data.append(serializer.data)
        for i in ser:
            if i is True:
                return ResponseData.fail('部分数据可能修改失败，请检查设置的用例')
        return ResponseData.success(f'设置为{request.data.get("name")}成功', data)

    @action(methods=['get'], detail=False)
    def get_case_obj_name(self, request: Request):
        """
         获取所有用例id和名称
         :param request:
         :return:
         """
        res = self.model.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)

    @action(methods=['GET'], detail=False)
    def get_page_steps_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        res = self.model.objects.filter(page=request.query_params.get('page_id')).values_list('id', 'name')
        return ResponseData.success('获取数据成功', [{'key': _id, 'title': name} for _id, name in res])
