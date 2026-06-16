# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.models import AiAgentContext
from src.apps.ai.views.agent_task import AiAgentTaskSerializer
from src.apps.user.views.user import UserSerializers
from src.common.tools.view.model_crud import ModelCRUD


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
        data["create_user"] = UserSerializers(instance=instance.create_user).data if instance.create_user_id else None
        return data


class AiAgentContextCRUD(ModelCRUD):
    model = AiAgentContext
    queryset = AiAgentContext.objects.all()
    serializer_class = AiAgentContextSerializer
    serializer = AiAgentContextSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["suite_id", "manual_case_id", "context_type", "context_hash", "task"]
