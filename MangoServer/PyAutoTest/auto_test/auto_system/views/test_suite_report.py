# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_user.views.test_object import TestObjectSerializers
from PyAutoTest.auto_test.auto_user.views.project_product import ProjectProductSerializersC
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.tools.view.model_crud import ModelCRUD


class TestSuiteReportSerializers(serializers.ModelSerializer):
    id = serializers.IntegerField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuiteReport
        fields = '__all__'


class TestSuiteReportSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    test_object = TestObjectSerializers(read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = TestSuiteReport
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'test_object',
            'user',
        )
        return queryset


class TestSuiteReportCRUD(ModelCRUD):
    model = TestSuiteReport
    queryset = TestSuiteReport.objects.all()
    serializer_class = TestSuiteReportSerializersC
    serializer = TestSuiteReportSerializers


class TestSuiteReportViews(ViewSet):
    model = TestSuiteReport
    serializer_class = TestSuiteReportSerializers
