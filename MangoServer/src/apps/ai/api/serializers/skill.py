# -*- coding: utf-8 -*-

from rest_framework import serializers

from src.apps.ai.models import AiSkill
from src.apps.user.formatters import format_user


class AiSkillSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiSkill
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("user", "update_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["user"] = format_user(instance.user) if instance.user_id else None
        data["update_user"] = format_user(instance.update_user) if instance.update_user_id else None
        return data
