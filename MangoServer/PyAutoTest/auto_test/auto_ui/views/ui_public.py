# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPublic
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiPublicSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicSerializersC(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)

    class Meta:
        model = UiPublic
        fields = '__all__'


class UiPublicCRUD(ModelCRUD):
    model = UiPublic
    queryset = UiPublic.objects.select_related('team').all()
    serializer_class = UiPublicSerializersC
    serializer = UiPublicSerializers


class UiPublicViews(ViewSet):
    model = UiPublic
    serializer_class = UiPublicSerializers

    @action(methods=['put'], detail=False)
    def test(self, request: Request):
        pass
