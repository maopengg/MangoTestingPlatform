# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiAssertions
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiAssertionsSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiAssertions
        fields = '__all__'


class ApiAssertionsCRUD(ModelCRUD):
    model = ApiAssertions
    queryset = ApiAssertions.objects.all()
    serializer_class = ApiAssertionsSerializers


class ApiAssertionsViews(ViewSet):

    @staticmethod
    def test(request):
        pass
