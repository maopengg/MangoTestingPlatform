# -*- coding: utf-8 -*-
from django.db.models import Count
from rest_framework import serializers

from src.apps.functional_test.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.functional_test.models import FunctionalTestDefect, FunctionalTestDefectCase
from src.apps.test_center.formatters.related import format_product_module_compact
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class FunctionalTestDefectRelationSerializer(serializers.ModelSerializer):
    case_no = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    plan_id = serializers.IntegerField(source="plan_case.plan_id", read_only=True)
    plan_name = serializers.CharField(source="plan_case.plan.name", read_only=True)
    snapshot = serializers.JSONField(source="plan_case.case_snapshot", read_only=True)
    result = serializers.IntegerField(source="plan_case.result", read_only=True)
    executor_name = serializers.CharField(source="plan_case.executor.name", read_only=True)
    execute_time = serializers.DateTimeField(
        source="plan_case.execute_time", format="%Y-%m-%d %H:%M:%S", read_only=True,
    )

    class Meta:
        model = FunctionalTestDefectCase
        fields = "__all__"

    @staticmethod
    def get_case_no(instance):
        if instance.case_id:
            return instance.case.case_no
        return (instance.plan_case.case_snapshot or {}).get("case_no") or instance.plan_case.case.case_no

    @staticmethod
    def get_case_title(instance):
        if instance.case_id:
            return instance.case.title
        return (instance.plan_case.case_snapshot or {}).get("title") or instance.plan_case.case.title


class FunctionalTestDefectSerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    resolved_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    closed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    case_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    plan_case_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = FunctionalTestDefect
        fields = "__all__"
        read_only_fields = ("defect_no", "status", "reporter", "update_user", "resolved_at", "closed_at")


class FunctionalTestDefectListSerializer(FunctionalTestDefectSerializer):
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_compact, read_only=True)
    reporter = RelatedObjectField(formatter=format_user, read_only=True)
    assignee = RelatedObjectField(formatter=format_user_simple, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    relations = serializers.SerializerMethodField()
    relation_count = serializers.SerializerMethodField()

    @staticmethod
    def get_relations(instance):
        return FunctionalTestDefectRelationSerializer(instance.case_relations.all(), many=True).data

    @staticmethod
    def get_relation_count(instance):
        value = getattr(instance, "relation_count", None)
        return value if value is not None else instance.case_relations.count()

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(ProductModuleService.with_full_paths(queryset, "module").annotate(
            relation_count=Count("case_relations", distinct=True),
        ).select_related(
            "project_product", "project_product__project", "module", "reporter", "assignee", "update_user",
        ).prefetch_related(
            "case_relations__case", "case_relations__plan_case__case", "case_relations__plan_case__plan",
            "case_relations__plan_case__executor",
        ))
