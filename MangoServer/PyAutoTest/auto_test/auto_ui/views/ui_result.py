# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiResult
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiResultSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiResult
        fields = '__all__'


class UiResultCRUD(ModelCRUD):
    model = UiResult
    queryset = UiResult.objects.all()
    serializer_class = UiResultSerializers


class UiResultViews(ViewSet):

    @staticmethod
    def test(request):
        pass
