# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import Database
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.auto_test.auto_system.views.project_config import TestObjectSerializers


class DatabaseSerializers(serializers.ModelSerializer):
    team = ProjectSerializers(read_only=True)
    test_obj = TestObjectSerializers(read_only=True)

    class Meta:
        model = Database
        fields = '__all__'


class DatabaseCRUD(ModelCRUD):
    model = Database
    queryset = Database.objects.select_related('team', 'test_obj').all()
    serializer_class = DatabaseSerializers


class DatabaseViews(ViewSet):

    @staticmethod
    def test(request):
        pass
