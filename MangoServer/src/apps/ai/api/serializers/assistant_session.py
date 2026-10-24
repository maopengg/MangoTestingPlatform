# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.models import AiAssistantSession
from src.apps.user.formatters import format_user


class AiAssistantSessionSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAssistantSession
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("create_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["create_user"] = format_user(instance.create_user) if instance.create_user_id else None
        return data
