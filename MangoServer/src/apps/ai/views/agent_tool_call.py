# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.models import AiAgentToolCall
from src.apps.ai.views.agent_task import AiAgentTaskSerializer
from src.apps.ai.views.mcp_server import AiMcpServerSerializer


class AiAgentToolCallSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentToolCall
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("task", "server")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["task"] = AiAgentTaskSerializer(instance=instance.task).data if instance.task_id else None
        data["server"] = AiMcpServerSerializer(instance=instance.server).data if instance.server_id else None
        return data
