# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.api.serializers.agent_task import AiAgentTaskSerializer
from src.apps.ai.models import AiAgentContext
from src.apps.user.formatters import format_user


class AiAgentContextSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentContext
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task", "create_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["task"] = AiAgentTaskSerializer(instance=instance.task).data if instance.task_id else None
        data["create_user"] = format_user(instance.create_user) if instance.create_user_id else None
        return data
