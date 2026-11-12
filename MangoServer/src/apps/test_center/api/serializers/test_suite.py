# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏

from django.db.models import Prefetch
from rest_framework import serializers

from src.apps.test_center.selectors.querysets import TestCenterQuerySelector

from src.apps.task_center.formatters import format_scheduled_task
from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers
from src.apps.test_center.api.serializers.project_product import ProjectProductSerializersC
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.apps.user.formatters import format_user
from src.common.validators.serializer_fields import RelatedObjectField


class TestSuiteOfflineExportSerializer(serializers.Serializer):
    source_kind = serializers.ChoiceField(choices=ReportSourceEnum.choices())
    source_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)


class TestSuiteOfflineOptionsSerializer(TestSuiteOfflineExportSerializer):
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class TestSuiteSerializers(serializers.ModelSerializer):
    id = serializers.IntegerField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'
        read_only_fields = ('diagnostic_file_path', 'report_retention_policy', 'retained_summary', 'report_retained')


class TestSuiteSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    tasks = RelatedObjectField(formatter=format_scheduled_task, read_only=True)
    user = RelatedObjectField(formatter=format_user, read_only=True)
    execution_summary = serializers.SerializerMethodField()
    report_conclusion = serializers.SerializerMethodField()
    automation_types = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = '__all__'
        read_only_fields = ('diagnostic_file_path', 'report_retention_policy', 'retained_summary', 'report_retained')

    @staticmethod
    def get_automation_types(obj):
        return sorted({row.type for row in getattr(obj, '_execution_summary_rows', [])})

    @staticmethod
    def get_execution_summary(obj):
        if obj.retained_summary:
            return obj.retained_summary['execution_summary']
        return TestSuiteSummaryService.effective_summary_from_rows(
            getattr(obj, '_execution_summary_rows', []),
        )

    @staticmethod
    def get_report_conclusion(obj):
        if obj.retained_summary:
            return obj.status
        rows = getattr(obj, '_execution_summary_rows', None)
        if rows is None:
            rows = obj.testsuitedetails_set.all()
        summary = TestSuiteSummaryService.effective_summary_from_rows(rows)
        return TestSuiteSummaryService.conclusion_status(obj.status, summary, summary['total'])

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(
            queryset,
            'module',
            'tasks__module',
        ).select_related(
            'project_product',
            'project_product__project',
            'tasks',
            'user',
        ).prefetch_related(
            'project_product__owners',
            Prefetch(
                'testsuitedetails_set',
                queryset=TestSuiteDetails.objects.only(
                    'id',
                    'test_suite_id',
                    'status',
                    'type',
                    'case_sum',
                    'success',
                    'fail',
                    'warning',
                    'is_excluded',
                ),
                to_attr='_execution_summary_rows',
            ),
        )
        return TestCenterQuerySelector.with_project_product_display(queryset)
