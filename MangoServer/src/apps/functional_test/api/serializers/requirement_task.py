# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.functional_test.models import FunctionalRequirementTask
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class FunctionalRequirementTaskSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalRequirementTask
        fields = "__all__"
        read_only_fields = ("update_user",)


class FunctionalRequirementTaskListSerializer(FunctionalRequirementTaskSerializer):
    owner = RelatedObjectField(formatter=format_user_simple, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("owner", "update_user", "requirement_version")
