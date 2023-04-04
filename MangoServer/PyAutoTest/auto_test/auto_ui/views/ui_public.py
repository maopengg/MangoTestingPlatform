# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPublic
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiPublicSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.all()
    serializer_class = UiPublicSerializers


class UiPublicViews(ViewSet):

    @staticmethod
    def test(request):
        pass
