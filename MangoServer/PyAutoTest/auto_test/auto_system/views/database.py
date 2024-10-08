# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import Database
from PyAutoTest.auto_test.auto_user.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_user.views.project_product import ProjectProductSerializersC
from PyAutoTest.tools.view.model_crud import ModelCRUD


class DatabaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Database
        fields = '__all__'


class DatabaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = Database
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            )
        return queryset


class DatabaseCRUD(ModelCRUD):
    model = Database
    queryset = Database.objects.all()
    serializer_class = DatabaseSerializersC
    serializer = DatabaseSerializers


class DatabaseViews(ViewSet):
    model = Database
    serializer_class = DatabaseSerializers
