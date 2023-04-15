# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.project_config import TestObjectSerializers
from PyAutoTest.auto_test.auto_ui.models import UiResult
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_case_group import UiCaseGroupSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiResultSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)
    case = UiCaseSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)
    case_group = UiCaseGroupSerializers(read_only=True)

    class Meta:
        model = UiResult
        fields = '__all__'


class UiResultSerializersC(serializers.ModelSerializer):
    class Meta:
        model = UiResult
        fields = '__all__'


class UiResultCRUD(ModelCRUD):
    model = UiResult
    queryset = UiResult.objects.select_related('team', 'case', 'test_obj', 'case_group').all()
    serializer_class = UiResultSerializers
    serializer = UiResultSerializersC


class UiResultViews(ViewSet):

    @staticmethod
    def test(request):
        pass
