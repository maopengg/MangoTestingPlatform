# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiAssertions
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiAssertionsSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiAssertions
        fields = '__all__'


class ApiAssertionsSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)
    case = ApiCaseSerializers(read_only=True)

    class Meta:
        model = ApiAssertions
        fields = '__all__'


class ApiAssertionsCRUD(ModelCRUD):
    model = ApiAssertions
    queryset = ApiAssertions.objects.all()
    serializer_class = ApiAssertionsSerializers
    serializer = ApiAssertionsSerializersC


class ApiAssertionsViews(ViewSet):
    model = ApiAssertions
    serializer_class = ApiAssertionsSerializers

    @action(methods=['put'], detail=False)
    def test(self, request: Request):
        pass
