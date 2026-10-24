# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.api.serializers.agent_task import AiAgentTaskSerializer
from src.apps.ai.models import AiAgentTaskStep
from src.apps.ai.services.core import mask_sensitive


class AiAgentTaskStepSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    start_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    end_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentTaskStep
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["task"] = AiAgentTaskSerializer(instance=instance.task).data if instance.task_id else None
        data["input_data"] = mask_sensitive(data.get("input_data") or {})
        data["output_data"] = mask_sensitive(data.get("output_data") or {})
        return data
