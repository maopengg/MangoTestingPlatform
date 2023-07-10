# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksSerializers
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiCaseGroupSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiCaseGroup
        fields = '__all__'


class UiCaseGroupSerializersC(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)
    time_name = TimeTasksSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)
    timing_actuator = UserSerializers(read_only=True)

    class Meta:
        model = UiCaseGroup
        fields = '__all__'


class UiCaseGroupCRUD(ModelCRUD):
    model = UiCaseGroup
    queryset = UiCaseGroup.objects.all()
    serializer_class = UiCaseGroupSerializersC
    serializer = UiCaseGroupSerializers


class UiCaseGroupViews(ViewSet):
    model = UiCaseGroup
    serializer_class = UiCaseGroupSerializers

    @action(methods=['put'], detail=False)
    def test(self, request: Request):
        pass
