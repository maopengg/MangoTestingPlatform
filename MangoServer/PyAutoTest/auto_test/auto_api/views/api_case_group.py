# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:57
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseGroup
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiCaseGroupSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCaseGroup
        fields = '__all__'


class ApiCaseGroupCRUD(ModelCRUD):
    model = ApiCaseGroup
    queryset = ApiCaseGroup.objects.all()
    serializer_class = ApiCaseGroupSerializers


class ApiCaseGroupViews(ViewSet):

    @staticmethod
    def test(request):
        pass
