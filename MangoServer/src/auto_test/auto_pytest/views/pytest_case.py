# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_pytest.views.pytest_module import PytestProjectModuleSerializersC
from src.auto_test.auto_pytest.views.pytest_project import PytestProjectSerializersC
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'


class PytestCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    pytest_project = PytestProjectSerializersC(read_only=True)
    module = PytestProjectModuleSerializersC(read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
        )
        return queryset


class PytestCaseCRUD(ModelCRUD):
    model = PytestCase
    queryset = PytestCase.objects.all()
    serializer_class = PytestCaseSerializersC
    serializer = PytestCaseSerializers


class PytestCaseViews(ViewSet):
    model = PytestCase
    serializer_class = PytestCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_test_case(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """

        return ResponseData.success(RESPONSE_MSG_0074)
