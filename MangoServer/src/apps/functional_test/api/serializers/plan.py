# -*- coding: utf-8 -*-
from django.db.models import Count, Q
from rest_framework import serializers

from src.apps.functional_test.api.serializers.iteration import FunctionalTestIterationListSerializer
from src.apps.functional_test.api.serializers.plan_mutation import FunctionalTestPlanSerializer
from src.apps.functional_test.api.serializers.suite import ManualTestSuiteSerializerC
from src.apps.functional_test.enums import (
    FunctionalTestResultEnum,
)
from src.apps.functional_test.models import (
    FunctionalTestPlanCase,
)
from src.apps.functional_test.services.suite import ManualTestSuiteService
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user, format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class FunctionalTestPlanListSerializer(FunctionalTestPlanSerializer):
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    requirement_version = ManualTestSuiteSerializerC(read_only=True)
    iteration = FunctionalTestIterationListSerializer(read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    case_count = serializers.IntegerField(read_only=True)
    execution_stats = serializers.SerializerMethodField()
    defect_count = serializers.IntegerField(read_only=True, default=0)
    open_defect_count = serializers.IntegerField(read_only=True, default=0)
    unlinked_failed_count = serializers.IntegerField(read_only=True, default=0)

    @staticmethod
    def get_execution_stats(instance):
        total = getattr(instance, "case_count", 0) or 0
        executed = getattr(instance, "executed_count", 0) or 0
        passed = getattr(instance, "passed_count", 0) or 0
        return {
            "total": total, "executed": executed, "passed": passed,
            "failed": getattr(instance, "failed_count", 0) or 0,
            "blocked": getattr(instance, "blocked_count", 0) or 0,
            "skipped": getattr(instance, "skipped_count", 0) or 0,
            "progress": round(executed / total * 100, 2) if total else 0,
            "pass_rate": round(passed / executed * 100, 2) if executed else 0,
        }

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.annotate(
            case_count=Count("plan_cases", distinct=True),
            executed_count=Count("plan_cases", filter=~Q(plan_cases__result=FunctionalTestResultEnum.UNEXECUTED.value),
                                 distinct=True),
            passed_count=Count("plan_cases", filter=Q(plan_cases__result=FunctionalTestResultEnum.PASSED.value),
                               distinct=True),
            failed_count=Count("plan_cases", filter=Q(plan_cases__result=FunctionalTestResultEnum.FAILED.value),
                               distinct=True),
            blocked_count=Count("plan_cases", filter=Q(plan_cases__result=FunctionalTestResultEnum.BLOCKED.value),
                                distinct=True),
            skipped_count=Count("plan_cases", filter=Q(plan_cases__result=FunctionalTestResultEnum.SKIPPED.value),
                                distinct=True),
            defect_count=Count("plan_cases__defect_relations__defect", distinct=True),
            open_defect_count=Count(
                "plan_cases__defect_relations__defect",
                filter=~Q(plan_cases__defect_relations__defect__status=4),
                distinct=True,
            ),
            unlinked_failed_count=Count(
                "plan_cases",
                filter=Q(
                    plan_cases__result__in=[
                        FunctionalTestResultEnum.FAILED.value,
                        FunctionalTestResultEnum.BLOCKED.value,
                    ],
                    plan_cases__defect_relations__isnull=True,
                ),
                distinct=True,
            ),
        ).select_related(
            "project_product", "project_product__project", "requirement", "requirement_version",
            "requirement_version__requirement", "iteration", "owner", "update_user",
        )


class FunctionalTestPlanCaseSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    execute_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    executor = RelatedObjectField(formatter=format_user_simple, read_only=True)
    defects = serializers.SerializerMethodField()
    open_defect_count = serializers.SerializerMethodField()

    class Meta:
        model = FunctionalTestPlanCase
        fields = "__all__"

    def to_representation(self, instance):
        data = dict(instance.case_snapshot or {})
        data.update(super().to_representation(instance))
        data["project_product_path"], data["module_path"] = ManualTestSuiteService.snapshot_paths(data, instance.case)
        data["owner_name"] = instance.case.owner.name
        data["executor_name"] = instance.executor.name if instance.executor else "-"
        return data

    @staticmethod
    def get_defects(instance):
        return [
            {
                "id": relation.defect_id,
                "defect_no": relation.defect.defect_no,
                "title": relation.defect.title,
                "status": relation.defect.status,
            }
            for relation in instance.defect_relations.all()
        ]

    @staticmethod
    def get_open_defect_count(instance):
        return sum(1 for relation in instance.defect_relations.all() if relation.defect.status != 4)
