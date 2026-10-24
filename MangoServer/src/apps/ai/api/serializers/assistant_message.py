# -*- coding: utf-8 -*-

from rest_framework import serializers

from src.apps.ai.models import AiAssistantMessage
from src.apps.ai.services.core import mask_sensitive


class AiAssistantMessageSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    need_confirm = serializers.SerializerMethodField()

    class Meta:
        model = AiAssistantMessage
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("session")

    @staticmethod
    def get_need_confirm(instance):
        return bool((instance.metadata or {}).get("need_confirm"))

    def to_representation(self, instance):
        from src.apps.ai.api.serializers.assistant_session import AiAssistantSessionSerializer

        data = super().to_representation(instance)
        data["session"] = AiAssistantSessionSerializer(instance=instance.session).data if instance.session_id else None
        data["tool_arguments"] = mask_sensitive(data.get("tool_arguments") or {})
        data["tool_result"] = mask_sensitive(data.get("tool_result") or {})
        data["metadata"] = mask_sensitive(data.get("metadata") or {})
        return data
