# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiRelyOn
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiRelyOnSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiRelyOn
        fields = '__all__'


class ApiRelyOnCRUD(ModelCRUD):
    model = ApiRelyOn
    queryset = ApiRelyOn.objects.all()
    serializer_class = ApiRelyOnSerializers


class ApiRelyOnViews(ViewSet):
    @staticmethod
    def test(request):
        pass
