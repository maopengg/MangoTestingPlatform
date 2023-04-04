# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class TestObjectSerializers(serializers.ModelSerializer):
    class Meta:
        model = TestObject
        fields = '__all__'


class TestObjectCRUD(ModelCRUD):
    model = TestObject
    queryset = TestObject.objects.all()
    serializer_class = TestObjectSerializers


class TestObjectViews(ViewSet):

    @staticmethod
    def test(request):
        pass
