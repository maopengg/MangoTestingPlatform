# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏

from rest_framework import serializers

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC
from src.apps.test_center.api.serializers.test_suite import TestSuiteSerializers
from src.apps.test_center.models import TestSuiteDetails


class TestSuiteDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuiteDetails
        fields = '__all__'
        read_only_fields = ('is_excluded', 'failure_reason', 'failure_description')


class TestSuiteDetailsSerializersC(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    test_suite = TestSuiteSerializers(read_only=True)

    class Meta:
        model = TestSuiteDetails
        fields = '__all__'

    @staticmethod
    def get_status(obj):
        from mangotools.enums import TaskEnum
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        if TestSuiteInfrastructureService.is_blocked(obj.summary_data):
            return TaskEnum.FAIL.value
        from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
        return TestSuiteSummaryService.public_status(obj.status)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'test_suite',
        ).prefetch_related('project_product__owners')
        return TestCenterQuerySelector.with_project_product_display(queryset)
