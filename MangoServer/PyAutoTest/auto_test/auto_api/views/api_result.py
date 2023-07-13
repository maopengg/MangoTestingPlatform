# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiResult
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_case_group import ApiCaseGroupSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers


class ApiResultSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiResult
        fields = '__all__'


class ApiResultSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    case = ApiCaseSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)
    case_group = ApiCaseGroupSerializers(read_only=True)

    class Meta:
        model = ApiResult
        fields = '__all__'


class ApiResultCRUD(ModelCRUD):
    model = ApiResult
    queryset = ApiResult.objects.all()
    serializer_class = ApiResultSerializersC
    serializer = ApiResultSerializers


class ApiResultViews(ViewSet):
    model = ApiResult
    serializer_class = ApiResultSerializers

    @action(methods=['put'], detail=False)
    def test(self, request: Request):
        pass
