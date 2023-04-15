# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.project_config import TestObjectSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiCaseGroupSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)

    class Meta:
        model = UiCaseGroup
        fields = '__all__'


class UiCaseGroupSerializersC(serializers.ModelSerializer):
    class Meta:
        model = UiCaseGroup
        fields = '__all__'


class UiCaseGroupCRUD(ModelCRUD):
    model = UiCaseGroup
    queryset = UiCaseGroup.objects.all()
    serializer_class = UiCaseGroupSerializers
    serializer = UiCaseGroupSerializersC


class UiCaseGroupViews(ViewSet):

    @staticmethod
    def test(request):
        pass
