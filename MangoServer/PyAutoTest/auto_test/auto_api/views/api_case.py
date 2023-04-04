# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiCaseSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseCRUD(ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializers


class ApiCaseViews(ViewSet):

    @staticmethod
    def test(request):
        pass
