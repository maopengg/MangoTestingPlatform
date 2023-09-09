# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:57
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseGroup
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiCaseGroupSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCaseGroup
        fields = '__all__'


class ApiCaseGroupSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ApiCaseGroup
        fields = '__all__'


class ApiCaseGroupCRUD(ModelCRUD):
    model = ApiCaseGroup
    queryset = ApiCaseGroup.objects.all()
    serializer_class = ApiCaseGroupSerializersC
    serializer = ApiCaseGroupSerializers


class ApiCaseGroupViews(ViewSet):
    model = ApiCaseGroup
    serializer_class = ApiCaseGroupSerializers

    @action(methods=['put'], detail=False)
    def put_type(self, request: Request):
        pass
