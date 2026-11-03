# -*- coding: utf-8 -*-
from django.db.models import Prefetch
from rest_framework import serializers

from src.apps.functional_test.api.serializers.automation_binding import ManualTestAutomationBindingLiteSerializer
from src.apps.functional_test.api.serializers.suite import ManualTestSuiteSerializerC
from src.apps.functional_test.models import (
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestCaseVersion,
)
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class ManualTestCaseBindingMixin:
    @staticmethod
    def setup_eager_loading(queryset):
        bindings = ManualTestAutomationBinding.objects.select_related("api_case", "ui_case")
        return queryset.prefetch_related(
            Prefetch(
                "manualtestautomationbinding_set",
                queryset=bindings,
                to_attr="prefetched_bindings",
            )
        )

    def get_bindings(self, obj):
        bindings = getattr(obj, "prefetched_bindings", None)
        if bindings is None:
            bindings = ManualTestAutomationBinding.objects.filter(
                manual_case=obj
            ).select_related("api_case", "ui_case")
        return ManualTestAutomationBindingLiteSerializer(
            instance=bindings,
            many=True,
        ).data


from src.apps.functional_test.api.serializers.case_mutation import ManualTestCaseSerializer


class ManualTestCaseListSerializer(ManualTestCaseBindingMixin, ManualTestCaseSerializer):
    bindings = serializers.SerializerMethodField()
    suite = ManualTestSuiteSerializerC(read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ManualTestCase
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(
            queryset,
            'module',
            'suite__module',
        ).select_related(
            "suite",
            "suite__project_product",
            "suite__project_product__project",
            "suite__module",
            "suite__iteration_ref",
            "suite__development_owner",
            "project_product",
            "project_product__project",
            "owner",
            "update_user",
        )
        return TestCenterQuerySelector.with_project_product_display(ManualTestCaseBindingMixin.setup_eager_loading(queryset))


class ManualTestCaseSerializerC(ManualTestCaseBindingMixin, ManualTestCaseSerializer):
    bindings = serializers.SerializerMethodField()
    suite = ManualTestSuiteSerializerC(read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(
            queryset,
            'module',
            'suite__module',
        ).select_related(
            "suite",
            "suite__project_product",
            "suite__project_product__project",
            "suite__module",
            "suite__owner",
            "project_product",
            "project_product__project",
            "owner",
            "update_user",
        )
        return TestCenterQuerySelector.with_project_product_display(ManualTestCaseBindingMixin.setup_eager_loading(queryset))


class ManualTestCaseVersionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    source_name = serializers.CharField(source="get_source_display", read_only=True)
    changed_by = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ManualTestCaseVersion
        fields = (
            "id",
            "case",
            "version_no",
            "snapshot",
            "source",
            "source_name",
            "changed_by",
            "create_time",
        )
