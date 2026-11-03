# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.functional_test.models import FunctionalTestRequirement
from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.formatters import format_user, format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class FunctionalTestRequirementSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestRequirement
        fields = "__all__"


class FunctionalTestRequirementSerializerC(FunctionalTestRequirementSerializer):
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    owner = RelatedObjectField(formatter=format_user, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return TestCenterQuerySelector.with_project_product_display(queryset.select_related(
            "project_product",
            "project_product__project",
            "owner",
            "update_user",
        ))
