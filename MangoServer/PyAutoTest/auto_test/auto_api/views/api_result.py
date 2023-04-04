# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiResult
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiResultSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiResult
        fields = '__all__'


class ApiResultCRUD(ModelCRUD):
    model = ApiResult
    queryset = ApiResult.objects.all()
    serializer_class = ApiResultSerializers


class ApiResultViews(ViewSet):

    @staticmethod
    def test(request):
        pass
