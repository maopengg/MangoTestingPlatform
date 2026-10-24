# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.auto_api.formatters import format_api_case
from src.apps.auto_ui.formatters import format_ui_case
from src.apps.functional_test.models import ManualTestAutomationBinding
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ManualTestAutomationBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    api_case = RelatedObjectField(formatter=format_api_case, read_only=True)
    ui_case = RelatedObjectField(formatter=format_ui_case, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"


class ManualTestAutomationBindingLiteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    automation_type_name = serializers.CharField(source="get_automation_type_display", read_only=True)
    relation_type_name = serializers.CharField(source="get_relation_type_display", read_only=True)
    optimize_status_name = serializers.CharField(source="get_optimize_status_display", read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"
