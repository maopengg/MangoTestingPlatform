# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.ai.api.serializers.skill import AiSkillSerializer
from src.apps.ai.models import (
    AiAgentArtifact,
    AiAgentEvent,
    AiAgentEvaluation,
    AiAgentTask,
    AiAgentTaskItem,
)
from src.apps.user.formatters import format_user


class AiAgentTaskSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentTask
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("skill", "create_user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["skill"] = AiSkillSerializer(instance=instance.skill).data if instance.skill_id else None
        data["create_user"] = format_user(instance.create_user) if instance.create_user_id else None
        if (instance.input_data or {}).get("mode") == "batch":
            status_names = {
                0: "fail",
                1: "success",
                2: "pending",
                3: "running",
                7: "pending",
                8: "running",
            }
            case_snapshots = {
                item.get("id"): item
                for item in (instance.input_data or {}).get("manual_case_snapshots") or []
            }
            items = []
            for item in AiAgentTaskItem.objects.filter(task=instance).order_by("item_order", "id"):
                snapshot = case_snapshots.get(item.manual_case_id) or {}
                items.append(
                    {
                        "manual_case_id": item.manual_case_id,
                        "case_no": snapshot.get("case_no") or "",
                        "title": snapshot.get("title") or "",
                        "status": status_names.get(item.status, "pending"),
                        "api_case_id": item.api_case_id,
                        "summary": (item.result_summary or {}).get("summary") or "",
                        "error_message": item.error_message or "",
                    }
                )
            data["output_data"] = {**(data.get("output_data") or {}), "items": items}
        return data


class AiAgentArtifactSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentArtifact
        fields = "__all__"


class AiAgentEventSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentEvent
        fields = "__all__"


class AiAgentEvaluationSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiAgentEvaluation
        fields = "__all__"
