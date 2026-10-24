# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.functional_test.models import (
    FunctionalTestIteration,
)
from src.apps.functional_test.services.iteration import FunctionalTestIterationService
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user, format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class FunctionalTestIterationSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestIteration
        fields = "__all__"

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        FunctionalTestIterationService.validate_dates(start_date, end_date)
        return attrs


class FunctionalTestIterationListSerializer(FunctionalTestIterationSerializer):
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    requirement_count = serializers.IntegerField(read_only=True, default=0)
    plan_count = serializers.SerializerMethodField()
    test_metrics = serializers.SerializerMethodField()
    open_defect_count = serializers.SerializerMethodField()

    @staticmethod
    def get_plan_count(instance):
        return (getattr(instance, "direct_plan_count", 0) or 0) + (
                getattr(instance, "version_plan_count", 0) or 0
        )

    @staticmethod
    def get_test_metrics(instance):
        total = (getattr(instance, "direct_case_count", 0) or 0) + (getattr(instance, "version_case_count", 0) or 0)
        executed = (getattr(instance, "direct_executed_count", 0) or 0) + (
                getattr(instance, "version_executed_count", 0) or 0)
        passed = (getattr(instance, "direct_passed_count", 0) or 0) + (
                getattr(instance, "version_passed_count", 0) or 0)
        return {
            "total": total,
            "executed": executed,
            "progress": round(executed / total * 100, 2) if total else 0,
            "pass_rate": round(passed / executed * 100, 2) if executed else 0,
        }

    @staticmethod
    def get_open_defect_count(instance):
        return getattr(instance, "open_defect_count", 0) or 0

    @staticmethod
    def setup_eager_loading(queryset):
        return FunctionalTestIterationService.list_with_stats(queryset).select_related(
            "project_product", "project_product__project", "owner", "update_user",
        )
