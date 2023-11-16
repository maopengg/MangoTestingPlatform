# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiInfo
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.project_module import ProjectModuleSerializers
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('api')


class ApiInfoSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiInfo
        fields = '__all__'


class ApiInfoSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    module_name = ProjectModuleSerializers(read_only=True)

    class Meta:
        model = ApiInfo
        fields = '__all__'


class ApiInfoCRUD(ModelCRUD):
    model = ApiInfo
    queryset = ApiInfo.objects.all()
    serializer_class = ApiInfoSerializersC
    serializer = ApiInfoSerializers


class ApiInfoViews(ViewSet):
    model = ApiInfo
    serializer_class = ApiInfoSerializers

    @action(methods=['get'], detail=False)
    def test(self, request: Request):
        pass
