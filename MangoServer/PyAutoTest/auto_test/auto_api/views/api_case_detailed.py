# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed
from PyAutoTest.auto_test.auto_api.service.automatic_parsing_interface import ApiParameter
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('api')


class ApiCaseDetailedSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedCRUD(ModelCRUD):
    model = ApiCaseDetailed
    queryset = ApiCaseDetailed.objects.all()
    serializer_class = ApiCaseDetailedSerializersC
    serializer = ApiCaseDetailedSerializers


class ApiCaseDetailedViews(ViewSet):
    model = ApiCaseDetailed
    serializer_class = ApiCaseDetailedSerializers

    @action(methods=['get'], detail=False)
    def test(self, request: Request):
        """
        同步接口
        @param request:
        @return:
        """
        pass