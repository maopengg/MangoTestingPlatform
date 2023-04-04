# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class NoticeConfigSerializers(serializers.ModelSerializer):
    class Meta:
        model = NoticeConfig
        fields = '__all__'


class NoticeConfigCRUD(ModelCRUD):
    model = NoticeConfig
    queryset = NoticeConfig.objects.all()
    serializer_class = NoticeConfigSerializers


class NoticeConfigViews(ViewSet):

    @staticmethod
    def test(request):
        pass
