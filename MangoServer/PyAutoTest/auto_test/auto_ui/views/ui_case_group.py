# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiCaseGroupSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiCaseGroup
        fields = '__all__'


class UiCaseGroupCRUD(ModelCRUD):
    model = UiCaseGroup
    queryset = UiCaseGroup.objects.all()
    serializer_class = UiCaseGroupSerializers


class UiCaseGroupViews(ViewSet):

    @staticmethod
    def test(request):
        pass
