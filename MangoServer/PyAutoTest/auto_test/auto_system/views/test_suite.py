# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestSuite
from PyAutoTest.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from PyAutoTest.auto_test.auto_system.views.tasks import TasksSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.tools.view.model_crud import ModelCRUD


class TestSuiteSerializers(serializers.ModelSerializer):
    id = serializers.IntegerField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'


class TestSuiteSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    tasks = TasksSerializers(read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'tasks',
            'user',
        )
        return queryset


class TestSuiteCRUD(ModelCRUD):
    model = TestSuite
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializersC
    serializer = TestSuiteSerializers
    # @error_response('system')
    # def get(self, request: Request):
    #     return ResponseData.success('')


class TestSuiteViews(ViewSet):
    model = TestSuite
    serializer_class = TestSuiteSerializers
