# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.data_producer.run_api import RunApi
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.project_module import ProjectModuleSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.exceptions.ui_exception import UiConfigQueryIsNoneError
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD


class UiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'


class UiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    module_name = ProjectModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'


class UiCaseCRUD(ModelCRUD):
    model = UiCase
    queryset = UiCase.objects.all()
    serializer_class = UiCaseSerializersC
    serializer = UiCaseSerializers


class UiCaseViews(ViewSet):
    model = UiCase
    serializer_class = UiCaseSerializers

    @action(methods=['get'], detail=False)
    def ui_case_run(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        case_json, res = RunApi(request.user).case(case_id=int(request.GET.get("case_id")),
                                                   test_obj=request.GET.get("testing_environment"))
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json.dict())
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', [case_json.dict()])

    @action(methods=['get'], detail=False)
    def ui_batch_run(self, request: Request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        try:
            case_json, res = RunApi(request.user).case_batch(case_id_list=eval(request.GET.get("case_id_list")),
                                                             test_obj=request.GET.get("testing_environment"))
        except UiConfigQueryIsNoneError as e:
            return ResponseData.fail(e.msg, code=e.code)
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json)
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', case_json)
