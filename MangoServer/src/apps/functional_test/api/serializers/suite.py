# -*- coding: utf-8 -*-
from django.db.models import Count, Q, Sum
from rest_framework import serializers

from src.apps.functional_test.api.serializers.iteration import FunctionalTestIterationListSerializer
from src.apps.functional_test.api.serializers.requirement import FunctionalTestRequirementSerializer
from src.apps.functional_test.api.serializers.suite_mutation import ManualTestSuiteSerializer
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.user.api.formatters import format_department
from src.apps.user.formatters import format_user, format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class ManualTestSuiteSerializerC(ManualTestSuiteSerializer):
    requirement = FunctionalTestRequirementSerializer(read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    development_owner = RelatedObjectField(formatter=format_user_simple, read_only=True)
    iteration_ref = FunctionalTestIterationListSerializer(read_only=True)
    delivery_team = RelatedObjectField(formatter=format_department, read_only=True)
    test_metrics = serializers.SerializerMethodField()
    task_metrics = serializers.SerializerMethodField()
    open_defect_count = serializers.IntegerField(read_only=True, default=0)

    @staticmethod
    def get_test_metrics(instance):
        total = getattr(instance, "plan_case_count", 0) or 0
        executed = getattr(instance, "executed_count", 0) or 0
        passed = getattr(instance, "passed_count", 0) or 0
        return {
            "total": total,
            "executed": executed,
            "progress": round(executed / total * 100, 2) if total else 0,
            "pass_rate": round(passed / executed * 100, 2) if executed else 0,
        }

    @staticmethod
    def get_task_metrics(instance):
        total = getattr(instance, "task_count", 0) or 0
        completed = getattr(instance, "completed_task_count", 0) or 0
        return {
            "total": total,
            "completed": completed,
            "progress": round(completed / total * 100, 2) if total else 0,
            "estimated_person_days": getattr(instance, "estimated_person_days", 0) or 0,
            "actual_person_days": getattr(instance, "actual_person_days", 0) or 0,
        }

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.annotate(
            plan_count=Count("test_plans", distinct=True),
            plan_case_count=Count("test_plans__plan_cases", distinct=True),
            executed_count=Count(
                "test_plans__plan_cases",
                filter=~Q(test_plans__plan_cases__result=0),
                distinct=True,
            ),
            passed_count=Count(
                "test_plans__plan_cases",
                filter=Q(test_plans__plan_cases__result=1),
                distinct=True,
            ),
            open_defect_count=Count(
                "test_plans__plan_cases__defect_relations__defect",
                filter=~Q(test_plans__plan_cases__defect_relations__defect__status=4),
                distinct=True,
            ) + Count(
                "defects",
                filter=~Q(defects__status=4),
                distinct=True,
            ),
            task_count=Count("requirement_tasks", distinct=True),
            completed_task_count=Count(
                "requirement_tasks", filter=Q(requirement_tasks__status=2), distinct=True,
            ),
            estimated_person_days=Sum("requirement_tasks__estimated_person_days"),
            actual_person_days=Sum("requirement_tasks__actual_person_days"),
        )
        return TestCenterQuerySelector.with_project_product_display(ProductModuleService.with_full_paths(queryset, 'module').select_related(
            "requirement",
            "previous_version",
            "iteration_ref",
            "delivery_team",
            "project_product",
            "project_product__project",
            "owner",
            "development_owner",
            "update_user",
        ))
